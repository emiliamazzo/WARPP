import os
import sys
import uuid
import json
import time
import asyncio
import importlib
import argparse
from typing import Optional, Any, Dict, Union, List, Tuple
from collections import deque
from pathlib import Path
from agents.extensions.models.litellm_model import LitellmModel
import litellm
# litellm._turn_on_debug()

import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel

import openai
from agents import (
    Agent, Runner, trace, TResponseInputItem, ToolCallItem, ToolCallOutputItem,
    HandoffOutputItem, MessageOutputItem, ItemHelpers, function_tool, 
    set_trace_processors, add_trace_processor, Trace, Span, Usage,
    RunHooks, RunConfig
)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Run the customer service application')
parser.add_argument('--human', action='store_true', help='Use human input instead of LLM client')
parser.add_argument('--domains', nargs='+', required=True, help='Specify the domains to process')
parser.add_argument('--parallelization', action='store_true', help='Enable parallel processing')
parser.add_argument('--intent', type=str, help='Specify a specific intent to process')
parser.add_argument('--prompt', type=str, choices=['Basic', 'ReAct'], help='Specify type of prompt to be used')
parser.add_argument('--model', type=str, help='Specify a model to use')
parser.add_argument('--api_key', type=str, help='Specify key for the model (non needed for OpenAI models)')

args = parser.parse_args()


### setting up the env vars for model and api key 
os.environ["AGENT_MODEL"]   = args.model
os.environ["AGENT_API_KEY"] = args.api_key
os.environ["PROMPT"] = args.prompt

parallelization_label = "parallel" if args.parallelization else "no_parallel"
exp_type = f"{parallelization_label}_{args.prompt}"
os.environ["EXP_TYPE"] = exp_type

clean_model_name = (
    "llama" if "llama" in args.model.lower() else
    "sonnet" if "sonnet" in args.model.lower() else
    "gpt" if "gpt" in args.model.lower() else
    args.model.lower()
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent_setup.setup import Result, setup_orchestrator_agent, setup_personalizer_agent #post getting keys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Client LLM Module Imports
from client_llm.instructions import client_prompt  
from client_llm.client_llm_utils import generate_llm_as_client_response, get_formatted_client_prompt  

# Tracing Imports
from tracing.setup import CustomTracingProcessor, UsageLogger

# Utility Imports
from utils import new_handle_agent_handoff, extract_tools, DOMAIN_TOOLS_MAPPING, save_routine_async, ALL_TOOL_MAPPING, on_llm_end_hook

# Model Imports
from models import AuthenticatedCustomerContext

usage_logger = UsageLogger(clean_model_name, exp_type, args.intent)
set_trace_processors([usage_logger])


    

async def run_personalizer(conversation_id, context, intent_identified, routine):
    """
    Runs the personalizer agent in parallel to generate a personalized routine for the client.
    
    Args:
        conversation_id (str): Unique identifier for the conversation.
        context (AuthenticatedCustomerContext): The context object holding customer and domain information.
        
    Returns:
        None
    """
    try:
        print('Personalizer workflow running...')
        intent = intent_identified
        personalizer_agent = setup_personalizer_agent()
        original_instruction = personalizer_agent.instructions  # keep original instructions
        available_tools = DOMAIN_TOOLS_MAPPING[intent]
        available_tools_names = [tool.name for tool in available_tools]


        customer_data_for_routine = str(context)
        
        extended_instruction = original_instruction.format(
            CLIENT_DATA=customer_data_for_routine,
            FULL_ROUTINE=routine,
            AVAILABLE_TOOLS=available_tools_names
        )
        
        print("\033[95m" + extended_instruction + "\033[0m")
        personalizer_agent.instructions = extended_instruction 

        # simplified context representation that's JSON serializable
        simplified_context = {
            "customer_id": context.customer_id,
            "domain": context.domain,
            # "intent_identified": context.intent_identified,
            "intent_identified": intent_identified,
            "client_info": context.client_info
        }

        personalizer_items: list[TResponseInputItem] = []
        personalizer_items.append({"content": f'User information: {simplified_context}', "role": "user"})

        print("Starting PersonalizerAgent in parallel...")
        result = await Runner.run(personalizer_agent, personalizer_items)
        intent_personalized_routine = None

        for item in result.new_items:
            if isinstance(item, MessageOutputItem):
                trimmed_tools_str = extract_tools(ItemHelpers.text_message_output(item))
                trimmed_tools = []
                for tool in available_tools:
                    if tool.name in trimmed_tools_str:
                        trimmed_tools.append(tool)

                trimmed_routine = ItemHelpers.text_message_output(item)
                
                intent_personalized_routine = f"\n{trimmed_routine}"
                context.intent_personalized_routine = intent_personalized_routine
                context.available_tools = trimmed_tools

                filename = f"output/trimmed_routines/{clean_model_name}/{exp_type}/{intent_identified}/{context.customer_id}_routine.txt"
                output_dir = os.path.dirname(filename)
                os.makedirs(output_dir, exist_ok=True)
                print('WE GOT HERE')
                # Save asynchronously without blocking
                asyncio.create_task(save_routine_async(filename, trimmed_routine))

                print(f"\033[32mPersonalizer Agent is done running. Routine has been uploaded\033[0m:")
                print(f"\033[32m{trimmed_routine}\033[0m:")
                return intent_personalized_routine, trimmed_tools
    except Exception as e:
        print(f"\033[91mError in personalizer: {e}\033[0m")


async def process_client(client_data: Dict, client_index: int, customer_id: int, domain: str = None, intent: str = None, llm_as_client = True, parallelization = True, model = 'gpt-4o') -> None:
    """
    Processes a single client interaction, running a conversation loop and agent calls.

    Args:
        TO DO LATER
    Returns:
        None
    """
    # Create a new context for each client 
    terminate_call = False
    complete_case_called = False
    personalizer_task = None  # Track personalizer task for parallel execution
    
    # Loop detection variables
    max_turns = 15  # Maximum number of conversation turns
    turn_counter = 0
    max_repeated_tool_calls = 3  # Max times a tool can be called with same args
    tool_call_history = deque(maxlen=10)  # Store recent tool calls
    repeated_tool_counter = {}  # Track repeated tool calls
    
    # Track tool names by call_id for dynamic results
    tool_call_mapping = {}  # call_id -> tool_name
    
    try:
        usage_logger.set_user_id(customer_id)
        context = AuthenticatedCustomerContext(
            customer_id=customer_id,
            domain=domain or client_data.get('domain')
        )
        
        # Create a new trace log for this client 
        output_file = f"output/trajectory/{clean_model_name}/{exp_type}/{intent}/{str(context.customer_id)}.jsonl"       
        # Ensure the directory exists
        output_dir = Path(output_file).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        if os.path.exists(output_file):
            os.remove(output_file)
        custom_processor = CustomTracingProcessor(output_file)
        
        # Validate domain and intent
        if not context.domain:
            print(f"Error: No domain specified for client {context.customer_id}")
            return
            
        # Create domain-specific orchestrator agent
        try:
            current_agent = setup_orchestrator_agent(context.domain, customer_id) 
        except ValueError as e:
            print(f"Error setting up orchestrator: {e}")
            return

        if llm_as_client:
            final_client_prompt = get_formatted_client_prompt(client_data, client_prompt)
        

        conversation_id = uuid.uuid4().hex[:10]  
        custom_processor.log_event('user_id', {
            'id': context.customer_id,
            'domain': context.domain,
            'intent': intent
        })
        
        input_items: list[TResponseInputItem] = []
        client_input_items: list[TResponseInputItem] = []  # For clean client LLM history

        print(f"\nStarting conversation for Client {client_index} - {context.customer_id}...\n")

        while True: 
            print('-'*200)
            print(context)
            print('-'*200)
            turn_counter += 1
            if turn_counter > max_turns:
                print(f"\033[91mWarning: Conversation exceeded {max_turns} turns. Terminating to prevent potential infinite loop.\033[0m")
                custom_processor.log_event('error', {
                    'current_agent': current_agent.name if hasattr(current_agent, 'name') else str(current_agent),
                    'error_message': f"Potential infinite loop detected: Exceeded {max_turns} conversation turns"
                })
                terminate_call = True
                break
                
            if terminate_call:
                break
                
            if llm_as_client:
                # Client LLM sees only clean conversation
                user_input = await generate_llm_as_client_response(client_input_items, final_client_prompt)
            else:
                user_input = input('Enter your response: ')
                
            if 'Exit.' in user_input:
                terminate_call = True
            
            # Add to both histories
            input_items.append({"content": user_input, "role": "user"})
            client_input_items.append({"content": user_input, "role": "user"})
            start_time = time.time()  # Start timing from when user input is received
            try:
                result = await Runner.run(current_agent, input_items, context=context)                
            except Exception as e:
                print(f"\033[91mError running agent {current_agent}: {e}\033[0m")
                custom_processor.log_event('error', {
                    'current_agent': current_agent,
                    'error_message': str(e)
                })
                custom_processor.write_logs()

                
            custom_processor.log_event('user_input', {'user_input': user_input})

            for new_item in result.new_items:
                
                new_agent = new_item.agent.name

                if isinstance(new_item, MessageOutputItem):
                    response = ItemHelpers.text_message_output(new_item)
                    end_time = time.time()
                    duration = round(end_time - start_time, 2)
                    custom_processor.log_event('agent_response', {'current_agent': new_agent,
                                                                 'agent_response': response,
                                                                 'user_perceived_latency': duration})

                    print(f"\033[34m{new_agent}\033[0m: {response}")
                    print(f"Time until response: {duration}")
                    
                    # Add clean response to client history
                    client_input_items.append({"content": response, "role": "assistant"})
                    
                    if complete_case_called:
                        terminate_call = True
                        custom_processor.write_logs()
                        break

                elif isinstance(new_item, HandoffOutputItem):
                    current_agent = result.last_agent    

                elif isinstance(new_item, ToolCallItem):
                    tool_name = new_item.raw_item.name
                    call_id = new_item.raw_item.call_id
                    tool_args = str(new_item.raw_item.arguments)
                    
                    # Store tool name for later use in ToolCallOutputItem
                    tool_call_mapping[call_id] = tool_name
                    
                    # Loop detection: Create a unique signature for this tool call
                    tool_signature = f"{tool_name}:{tool_args}"
                    
                    # Check if this exact tool call has been made recently
                    if tool_signature in tool_call_history:
                        if tool_signature not in repeated_tool_counter:
                            repeated_tool_counter[tool_signature] = 1
                        else:
                            repeated_tool_counter[tool_signature] += 1
                            
                        # If a tool is being called repeatedly with the same args, it might be an infinite loop
                        if repeated_tool_counter[tool_signature] >= max_repeated_tool_calls:
                            print(f"\033[91mWarning: Tool '{tool_name}' called repeatedly with same arguments. Terminating to prevent infinite loop.\033[0m")
                            custom_processor.log_event('error', {
                                'current_agent': new_agent,
                                'error_message': f"Potential infinite loop detected: Tool '{tool_name}' called {repeated_tool_counter[tool_signature]} times with same arguments"
                            })
                            terminate_call = True
                            break
                    
                    # Add to history
                    tool_call_history.append(tool_signature)
                    
                    print(f"{new_agent}: Calling a tool")
                    print(f"Tool name: {new_item.raw_item.name}")
                    print(f"arguments: {new_item.raw_item.arguments}")
                    custom_processor.log_event('tool_called', {'current_agent': new_agent,
                                                            'tool_name': new_item.raw_item.name,
                                                            'call_id': new_item.raw_item.call_id,
                                                            'arguments': new_item.raw_item.arguments})
                    ## end conversation if complete case was called
                    if new_item.raw_item.name == 'complete_case':
                        complete_case_called = True


                elif isinstance(new_item, ToolCallOutputItem):
                    # Save dynamic function results for ground truth generation
                    call_id = new_item.raw_item.get('call_id')
                    if call_id and call_id in tool_call_mapping:
                        tool_name = tool_call_mapping[call_id]
                        await save_dynamic_result_to_customer_data(
                            context.customer_id,
                            context.domain,
                            tool_name,
                            new_item.output
                        )
                        # Clean up the mapping to avoid memory leaks
                        del tool_call_mapping[call_id]
                    
                    if isinstance(new_item.output, dict):
                        if 'error' in new_item.output:
                            print(f"\033[91mError: {new_item.output['error']}\033[0m")
                            continue
                            
                        if 'intent' in new_item.output:
                            intent_identified = new_item.output.get("intent")
                            routine = new_item.output.get("routine")
                            info_tools = new_item.output.get("info_gathering_tools")
                            execution_tools = new_item.output.get("execution_tools")
                            
                            intent_full_routine = f'The customer ID is {context.customer_id}. \n Routine to execute: \n {routine}'
                            intent_all_tools = ALL_TOOL_MAPPING[intent_identified]
                           
                            if parallelization:
                                for tool_func in info_tools:
                                    try:
                                        tool_result = await tool_func(context)
                                        context.update_client_info(tool_result)
                                        asyncio.create_task( #make it run in background 
                                            save_dynamic_result_to_customer_data(
                                                context.customer_id,
                                                context.domain,
                                                tool_func.__name__,
                                                tool_result,
                                                info_tool=True
                                            )
                                        )
                                        print(f'\033[92mSuccessfully executed {tool_func.__name__} and updated context\033[0m')
                                    except Exception as e:
                                        print(f"\033[91mError executing tool {tool_func.__name__}: {e}\033[0m")
                                
                                print(f"\033[94mIdentified intent: {intent_identified}, starting personalizer in parallel...\033[0m")
                                
                                # start personalizer task in parallel (non-blocking)
                                personalizer_task = asyncio.create_task(run_personalizer(conversation_id, context, intent_identified, intent_full_routine))

                            else:
                                intent_personalized_routine, available_tools = None, None   

                    if isinstance(new_item.output, Result): 
                        if personalizer_task is not None:
                            print(f"\033[94mWaiting for personalizer to complete...\033[0m")
                            intent_personalized_routine, available_tools = await personalizer_task
                            personalizer_task = None  # Reset to avoid re-awaiting
                        else:
                            intent_personalized_routine, available_tools = None, None
                            
                        new_handle_agent_handoff(new_item.output.agent, context, intent_identified, intent_personalized_routine, available_tools, intent_full_routine, intent_all_tools, parallelization = parallelization)
                        current_agent = new_item.output.agent
                    
                    custom_processor.log_event('tool_output', {
                        'current_agent': new_agent,
                        'call_id': new_item.raw_item.get('call_id'),
                        'result': new_item.output
                    })

                custom_processor.write_logs()
                all_inputs = result.to_input_list()
                
                ####Filter all inputs so that the returns from intent identified are not passed to agent 
                # A) find call IDs for Intent Identified function call to remove from history to 
                intent_call_ids = {
                    itm["call_id"]
                    for itm in all_inputs
                    if itm.get("type") == "function_call" 
                       and itm.get("name") == "intent_identified"
                }
                
                # B) filter them out
                input_items = [
                    itm
                    for itm in all_inputs
                    if itm.get("call_id") not in intent_call_ids
                ]
                
    except Exception as e:
        print(f"Error processing client {client_index}: {e}")
        custom_processor.log_event('error', {
                    'current_agent': current_agent,
                    'error_message': str(e)
                })
    finally:
        custom_processor.write_logs()

async def save_dynamic_result_to_customer_data(customer_id: str, domain: str, tool_name: str, result: Any, info_tool: bool = False) -> None:
    """
    Save dynamic result to customer data file.
    
    Args:
        customer_id: ID of the customer
        domain: Domain name (kept for backward compatibility)
        tool_name: Name of the tool that generated the result
        result: The result to save
    """
        
    try:
        input_file = f"test_data/customer_data/{domain}_utterance.json"
        
        #  output directory based on prompt type and parallelization
        if args.prompt == "ReAct":
            output_dir = f"output/dynamic_results/{clean_model_name}/basic_react"
        else:  # Basic prompt
            parallelization_str = "parallel" if args.parallelization else "no_parallel"
            output_dir = f"output/dynamic_results/{clean_model_name}/{parallelization_str}/Basic"
            
        output_file = f"{output_dir}/{domain}_utterance.json"
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Determine which file to read from - prefer output file if it exists
        file_to_read = output_file if os.path.exists(output_file) else input_file
        
        if not os.path.exists(file_to_read):
            print(f"Warning: Customer data file {file_to_read} does not exist")
            return
            
        with open(file_to_read, 'r') as f:
            customer_data = json.load(f)
            
        customer_found = False
        for record in customer_data:
            # Handle different customer ID field names
            record_customer_id = str(record.get('customer_id') or record.get('customerId') or record.get('patientId', ''))
            
            if record_customer_id == str(customer_id):
                customer_found = True
                # choose top-level key based on info_tool flag
                top_key = 'info_gathering_results' if info_tool else 'dynamic_results'
                if top_key not in record:
                    record[top_key] = {}
                # make sure result is JSON serializable
                try:
                    json.dumps(result)
                    serializable = result
                except (TypeError, ValueError):
                    serializable = str(result)
                # store result under tool_name
                record[top_key][tool_name] = serializable
                break
                
        if not customer_found:
            print(f"Warning: Customer {customer_id} not found in {file_to_read}")
            return
            
        with open(output_file, 'w') as f:
            json.dump(customer_data, f, indent=2)
            
        print(f"Saved dynamic result for tool '{tool_name}' for customer {customer_id} to {output_file}")
            
    except Exception as e:
        print(f"Error saving dynamic result: {e}")

async def main():
    """
    Main function to handle command-line arguments and process client data.

    Parses command line arguments and processes client data according to the specified domains.

    Returns:
        None
    """
    try:
            
        client_count = 0

        for domain in args.domains:
            path = os.path.abspath(f'test_data/customer_data/{domain}_utterance.json')
            if not os.path.exists(path):
                print(f"Warning: No file found for domain '{domain}' at {path}")
                continue

            print(f"\nLoading records from {path}…")
            with open(path, 'r', encoding='utf-8') as f:
                records = json.load(f)

            if not isinstance(records, list):
                print(f"Error: Expected a JSON list in {path}, but got {type(records).__name__}")
                continue
                
            
            print(f"Processing {len(records)} records for domain '{domain}'…")
            for index, record in enumerate(records):
                intent = record["agent_sequence"][0]
                customer_id = record["customer_id"] or record["patient_id"]
                print('CUSTOMER_ID', customer_id)
                record['intent'] = intent #reinject it as intent 
                
                # Skip if specific intent is requested and doesn't match
                if args.intent and intent != args.intent:
                    continue
                
                trajectory_file = f"output/trajectory/{clean_model_name}/{exp_type}/{intent}/{str(customer_id)}.jsonl"
                
                if os.path.exists(trajectory_file):
                    print(f"Skipping {domain} client {customer_id} - trajectory already exists")
                    continue
                    
                await process_client(
                    record,
                    client_count,
                    customer_id = customer_id, 
                    domain=domain,
                    intent = intent,
                    llm_as_client=not args.human,
                    parallelization=args.parallelization,
                    model=args.model
                )
                client_count += 1

                # if client_count >= 2:  # Add this check to stop after 1 client
                #     print("\nCompleted processing 1 client. Stopping...")
                #     return
    
    except Exception as e:
        print(f"Error loading customer data: {e}")
        return

if __name__ == "__main__":
    asyncio.run(main())
