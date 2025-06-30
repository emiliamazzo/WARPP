import os
import sys
import uuid
import json
import time
import asyncio
import argparse
from typing import Optional, Any, Dict, Union, List, Tuple
from collections import deque
from pathlib import Path
from react_utils import setup_environment, initialize_model_backend, load_domain_tools_and_routines, format_intents_prompt_section, get_tool_description, get_tool_name, ensure_dirs, save_dynamic_result_to_customer_data
from config import BASE_DIR, EXP_TYPE, OUTPUT_ROOT, REACT_TRAJECTORY, DOMAIN_INTENTS
from example import react_example
import re
import pandas as pd
from pydantic import BaseModel
from agents.extensions.models.litellm_model import LitellmModel
import litellm

from agents import (Agent, Runner, trace, TResponseInputItem, ToolCallItem, ToolCallOutputItem,
    HandoffOutputItem, MessageOutputItem, ItemHelpers, function_tool, set_trace_processors,
    add_trace_processor, Trace, Span, Usage,RunHooks, RunConfig)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from client_llm.instructions import client_prompt  
from client_llm.client_llm_utils import generate_llm_as_client_response, get_formatted_client_prompt
from tracing.setup import CustomTracingProcessor, UsageLogger
from models import AuthenticatedCustomerContext
from utils import (DOMAIN_TOOLS_MAPPING, CLIENT_INFO_TOOLS_MAPPING, CLIENT_INFO_TOOLS_EXTRA_MAPPING,
    ROUTINE_MAPPING, ALL_TOOL_MAPPING, complete_case)
from agent_setup.setup import send_verification_text, code_verifier 



def create_react_agent(domain: str, customer_id: str, domain_specific_prompt: str) -> Agent:
    """Create ReAct agent with ALL domain tools and routines from the start"""
    
    auth_tools = [send_verification_text, code_verifier]
    domain_tools = DOMAIN_ALL_TOOLS.get(domain, [])
    all_tools = auth_tools + domain_tools
    
    domain_routines = DOMAIN_ALL_ROUTINES.get(domain, "")
    

    tool_descriptions = "\n".join([
        f"- {get_tool_name(tool)}: {get_tool_description(tool)}" 
        for tool in all_tools
    ])
    
    react_instructions = f"""
You are an AI agent helping with customer service in the {domain} domain for customer {customer_id}. You must reason through customer requests step by step using the format: Thought → Action. The Observation of the action appears in your context. 


{domain_specific_prompt}
---
**MANDATORY FORMAT - YOU MUST USE THIS STRUCTURE:**
Use the following structure at every step:

Thought N: Your reasoning for what to do next.
Action N: Your action.  
    - If replying to the user, use `Respond: …`.  
    - If calling a tool:  
        1. Write a natural language narration in the `Action` fields (e.g., `Action 2: Call send_verification_text(phone_number=2821863372)`).
        2. Then, actually call the tool by emitting a function call using OpenAI’s tool-calling interface

**IMPORTANT: You are the only agent. There are no other specialists, teams, or agents.**
    -You alone are responsible for both authentication and fulfilling the customer's request.
    -Never say that a specialist, another agent, or a different team will assist.

**EXAMPLE - COPY THIS EXACT SYNTAX:**
{react_example}

Remember:
-** You must always use the following format for your response:**
    **Thought N:** Your reasoning for what to do next.
    **Action N:** Your action.  
        - If replying to the user, use `Respond: …`.  
        - If calling a tool:  
            1. Write a natural language narration in the `Action` fields (e.g., `Action 2: Call send_verification_text(phone_number=2821863372)`).
            2. Then, actually call the tool by emitting a function call using OpenAI’s tool-calling interface
-You are responsible for authentication and fulfilling the user request. There are no other specialist agents.
"""

    print(react_instructions)
    try:
        agent = Agent(
            name="ReActAgent",
            model=MODEL_BACKEND,
            tools=all_tools,
            instructions=react_instructions
        )
        return agent
    except Exception as e:
        print(f"Failed to create ReAct agent: {e}")
        raise



        
async def process_client_react(domain_specific_prompt: str, client_data: Dict, client_index: int, customer_id: int, domain: str = None, intent: str = None, llm_as_client = True) -> None:
    """Process a single client using ReAct methodology"""
    
    terminate_call = False
    complete_case_called = False
    max_turns = 25  # slightly higher since we need to handle more in react
    turn_counter = 0
    authenticated = False
    
    # track tool names by call_id for dynamic results
    tool_call_mapping = {}  # call_id ->tool_name
    
    try:
        intent_folder = intent if intent else "react_session"
        output_file = os.path.abspath(os.path.join(BASE_DIR,'output','trajectory',clean_model_name,'react',intent_folder,f"{customer_id}.jsonl"))
        print(f"Creating output file: {output_file}")
        
        output_dir = Path(output_file).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        if os.path.exists(output_file):
            os.remove(output_file)
        custom_processor = CustomTracingProcessor(output_file)
        
        #create context
        context = AuthenticatedCustomerContext(
            customer_id=str(customer_id),
            domain=str(domain)
        )
        print(f"Created context for customer {customer_id}, domain {domain}")
        
        usage_logger.set_user_id(customer_id)
        
        # create react agent with all domain tools
        print(f"Creating ReAct agent for domain {domain}, customer {customer_id}")

        try:
            react_agent = create_react_agent(str(domain), str(customer_id), domain_specific_prompt)
            print(f"ReAct agent created successfully")
        except Exception as e:
            print(f"Error creating ReAct agent: {e}")
            return
        
        if llm_as_client:
            final_client_prompt = get_formatted_client_prompt(client_data, client_prompt)
        
        custom_processor.log_event('user_id', {
            'id': customer_id,
            'domain': domain,
            'intent': intent,
            'system_type': 'react'
        })
        
        input_items: list[TResponseInputItem] = []
        client_input_items: list[TResponseInputItem] = []  # for client LLM only
        
        print(f"\nStarting ReAct conversation for Client {client_index} - {customer_id}...\n")
        
        while True:
            print('\033[93m' + str(client_input_items) + '\033[0m')
            turn_counter += 1
            if turn_counter > max_turns:
                print(f"\033[91mWarning: Conversation exceeded {max_turns} turns. Terminating.\033[0m")
                custom_processor.log_event('error', {
                    'current_agent': 'ReActAgent',
                    'error_message': f"Exceeded {max_turns} conversation turns"
                })
                break
                
            if terminate_call:
                break
            
            if llm_as_client:
                try:
                    # use client_input_items for LLM client (only customer messages)
                    user_input = await generate_llm_as_client_response(client_input_items, final_client_prompt)
                    print(f"Client input: {user_input}")
                except Exception as e:
                    print(f"Error generating client response: {e}")
                    break
            else:
                user_input = input('Enter your response: ')
            if 'Exit.' in user_input:
                terminate_call = True
            
            # add user input to BOTH histories
            input_items.append({"content": user_input, "role": "user"})
            client_input_items.append({"content": user_input, "role": "user"})
            
            start_time = time.time()
            
            try:
                result = await Runner.run(react_agent, input_items, context=context)
                print(f"ReAct agent run completed successfully")
            except Exception as e:
                print(f"\033[91mError running ReAct agent: {e}\033[0m")
                print(f"\033[91mError type: {type(e)}\033[0m")
                import traceback
                print(f"\033[91mTraceback: {traceback.format_exc()}\033[0m")
                custom_processor.log_event('error', {
                    'current_agent': 'ReActAgent',
                    'error_message': str(e),
                    'error_type': str(type(e)),
                    'turn_counter': turn_counter
                })
                break
            
            custom_processor.log_event('user_input', {'user_input': user_input})
            
            for new_item in result.new_items:
                if isinstance(new_item, MessageOutputItem):
                    full_response = ItemHelpers.text_message_output(new_item)
                    customer_message = None ### resetting the variable here
                    end_time = time.time()
                    duration = round(end_time - start_time, 2)

                    ## get every action line
                    actions = re.findall(r"(?im)^action\s+\d+\s*:\s*(.*)$", full_response)

                    print('\033[93m' + 'actions' + '\033[0m', actions)
                    
                    if actions:
                        last_act = actions[-1]
                        if not last_act.strip(): #empty placeholder action for tool call
                            continue

                        last_act = last_act.strip()

                        m = re.search(
                            r"(?im)^Action\s+\d+\s*:\s*Respond\s*:\s*(?P<msg>.*?)"
                            r"(?=(?:^Action\s+\d+|^Thought\s+\d+)|\Z)",
                            full_response,
                            flags=re.MULTILINE | re.DOTALL
                        )


                        if m:
                            # grab everything after "Respond:" up to the next Action/Thought or end
                            customer_message = m.group("msg").strip()
            
                        #agent action is tool call: do not show message until after tool call
                        elif "(" in last_act and ")" in last_act:
                            # It’s a tool call → *no* user‐facing message now
                            print(f"\033[90m[Debug - Full ReAct reasoning]:\033[0m")
                            print(f"\033[90m{full_response}\033[0m")
                            print(f"\033[90m[End Debug]\033[0m")
                            continue

                        
                    else:
                        # wrong formatting so we just return the full mesasge
                        customer_message = full_response.strip()

                    custom_processor.log_event('agent_response', {
                        'current_agent': 'ReActAgent',
                        'full_react_reasoning': full_response,  
                        'customer_message': customer_message,  
                        'user_perceived_latency': duration
                    })
                    
                    # show only the customer-facing message to the client
                    if customer_message is not None:
                        print(f"\033[34mReActAgent\033[0m: {customer_message}")
                        print(f"Time until response: {duration}")
                    
                    # debug: also show the full reasoning
                    print(f"\033[90m[Debug - Full ReAct reasoning]:\033[0m")
                    print(f"\033[90m{full_response}\033[0m")
                    print(f"\033[90m[End Debug]\033[0m")
                    
                    # add extracted customer message to client history
                    if customer_message is not None:
                        client_input_items.append({"content": customer_message, "role": "assistant"})
                    
                    if complete_case_called:
                        terminate_call = True
                        custom_processor.write_logs()
                        break
                
                elif isinstance(new_item, ToolCallItem):
                    tool_name = new_item.raw_item.name
                    call_id = new_item.raw_item.call_id
                    
                    tool_call_mapping[call_id] = tool_name
                    
                    print(f"\n\033[94mReActAgent: Calling tool {tool_name}\033[0m")
                    print(f"\033[94mArguments: {new_item.raw_item.arguments}\033[0m")
                    
                    custom_processor.log_event('tool_called', {
                        'current_agent': 'ReActAgent',
                        'tool_name': tool_name,
                        'call_id': call_id,
                        'arguments': new_item.raw_item.arguments
                    })
                    
                    if tool_name == 'complete_case':
                        complete_case_called = True
                    elif tool_name == 'code_verifier':
                        # track authentication state
                        authenticated = True
                
                elif isinstance(new_item, ToolCallOutputItem):
                    print(f" call_id: {new_item.raw_item.get('call_id')}")
                    print(f" tool_call_mapping: {tool_call_mapping}")
                    print(f"output type: {type(new_item.output)}")
                    print(f"output: {new_item.output}")
                    
                    # save dynamic function results and store tool name before cleanup
                    call_id = new_item.raw_item.get('call_id')
                    tool_name = None
                    if call_id and call_id in tool_call_mapping:
                        tool_name = tool_call_mapping[call_id]
                        output = new_item.output
                        print(f"  ✅ Found tool: {tool_name}")
                        await save_dynamic_result_to_customer_data(
                            str(customer_id), str(domain), tool_name, new_item.output, clean_model_name
                        )

                        # convert output to something JSON-serializable:
                        if hasattr(output, 'value'):
                            serializable_output = {"value": output.value}
                        else:
                            serializable_output = output

                        
                        observation_text = f"Observation: {serializable_output}"
                        input_items.append({"role": "assistant", "content": observation_text})

                        # clean mapping to avoid memory leak
                        del tool_call_mapping[call_id]
                    
                    if isinstance(new_item.output, dict):
                        if 'error' in new_item.output:
                            print(f"\033[91mError: {new_item.output['error']}\033[0m")
                            continue
                    
                    custom_processor.log_event('tool_output', {
                        'current_agent': 'ReActAgent',
                        'call_id': call_id,
                        'result': new_item.output
                    })
            
            # full history for ReAct agent
            input_items = result.to_input_list()
            
            custom_processor.write_logs()
    
    except Exception as e:
        print(f"Error processing ReAct client {client_index}: {e}")
    finally:
        custom_processor.write_logs()

async def main():
    """Main function for ReAct baseline"""
    try:
        global DOMAIN_ALL_TOOLS, DOMAIN_ALL_ROUTINES, clean_model_name, usage_logger, MODEL_BACKEND

        args, model_name, clean_model_name, intent, api_key = setup_environment()
        usage_logger = UsageLogger(clean_model_name, 'react', intent)
        set_trace_processors([usage_logger])

        MODEL_BACKEND = initialize_model_backend(model_name, api_key)
        DOMAIN_ALL_TOOLS, DOMAIN_ALL_ROUTINES, INTENT_TOOLS, INTENT_ROUTINES = load_domain_tools_and_routines()
        client_count = 0
        
        for domain in args.domains:
            path = os.path.abspath(os.path.join(BASE_DIR, 'test_data', 'customer_data', f'{domain}_utterance.json'))
            if not os.path.exists(path):
                print(f"Warning: No file found for domain '{domain}' at {path}")
                continue
            
            print(f"\nLoading records from {path}...")
            
            with open(path, 'r', encoding='utf-8') as f:
                records = json.load(f)
            
            if not isinstance(records, list):
                print(f"Error: Expected a JSON list in {path}")
                continue

            domain_specific_prompt = format_intents_prompt_section(INTENT_TOOLS, INTENT_ROUTINES, DOMAIN_INTENTS[domain])
            
            print(f"Processing {len(records)} records for domain '{domain}'...")
            
            for index, record in enumerate(records):
                try:
                    customer_id = record.get("customer_id") or record.get("patient_id")
                    
                    if not customer_id:
                        print(f"Warning: No customer_id found in record {index}, skipping")
                        continue
                    
                    # get intent for filtering if --intent is specified
                    intent_for_filtering = None
                    agent_sequence = record.get("agent_sequence", [])
                    if agent_sequence and len(agent_sequence) > 0:
                        intent_for_filtering = agent_sequence[0]
                    
                    # skip if specific intent is requested and doesn't match
                    if args.intent and intent_for_filtering != args.intent:
                        continue
                    
                    print(f"Processing record {index}: customer_id={customer_id}, domain={domain}")
                    
                    record['intent'] = intent_for_filtering if intent_for_filtering else "customer_service_request"
                    
                    # check if trajectory already exists
                    intent_folder = intent_for_filtering if intent_for_filtering else "react_session"
                    trajectory_file = os.path.join(BASE_DIR, 'output', 'trajectory', clean_model_name, 'react', intent_folder, f'{str(customer_id)}.jsonl')

                    if os.path.exists(trajectory_file):
                        print(f"Skipping {domain} client {customer_id} - ReAct trajectory already exists")
                        continue
                    
                    await process_client_react(
                        domain_specific_prompt,
                        record,
                        client_count,
                        customer_id=customer_id,
                        domain=domain,
                        intent=intent_for_filtering,
                        llm_as_client=not args.human
                    )
                    client_count += 1
                    
                except Exception as e:
                    print(f"Error processing record {index}: {e}")
                    continue
    
    except Exception as e:
        print(f"Error in ReAct main: {e}")
        return

if __name__ == "__main__":
    asyncio.run(main()) 