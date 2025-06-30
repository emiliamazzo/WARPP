import os
import sys
from typing import Optional, Any
import json 
import inspect
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agents.extensions.models.litellm_model import LitellmModel
from agent_setup.setup import send_verification_text, code_verifier 
from utils import (
    DOMAIN_TOOLS_MAPPING, CLIENT_INFO_TOOLS_MAPPING, CLIENT_INFO_TOOLS_EXTRA_MAPPING,
    ROUTINE_MAPPING, ALL_TOOL_MAPPING, complete_case)
from config import BASE_DIR, EXP_TYPE, OUTPUT_ROOT, REACT_TRAJECTORY, DOMAIN_INTENTS

def ensure_dirs(clean_model_name: str):
    dirs = [
        OUTPUT_ROOT,
        REACT_TRAJECTORY / clean_model_name / "react",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    
def setup_environment():
    parser = argparse.ArgumentParser(description='Run the ReAct customer service application')
    parser.add_argument('--human', action='store_true', help='Use human input instead of LLM client')
    parser.add_argument('--domains', nargs='+', required=True, help='Specify the domains to process')
    parser.add_argument('--intent', type=str, help='Specify a specific intent to process')
    parser.add_argument('--model', type=str, required=True, help='Specify a model to use')
    parser.add_argument('--api_key', type=str, help='Specify key for the model')
    args = parser.parse_args()

    # Clean model name
    model_lower = args.model.lower()
    clean_model_name = (
        "llama" if "llama" in model_lower else
        "sonnet" if "sonnet" in model_lower else
        "gpt" if "gpt" in model_lower else
        model_lower
    )

    os.environ["EXP_TYPE"] = "basic_react"
    os.environ["AGENT_MODEL"] = args.model
    os.environ["AGENT_API_KEY"] = args.api_key or ""

    ensure_dirs(clean_model_name)

    return args, args.model, clean_model_name, args.intent, args.api_key

    

def initialize_model_backend(model_name: str, api_key: str = None):
    """
    Validates the API key and creates the MODEL_BACKEND instance.
    Raises an error and exits if validation fails or creation errors out.
    """
    try:
        if not api_key and not os.environ.get("AGENT_API_KEY"):
            raise ValueError("No API key available. Please provide --api_key or set environment variable.")
        
        final_api_key = api_key or os.environ.get("AGENT_API_KEY", "")
        if not final_api_key.strip():
            raise ValueError("Empty API key provided.")
        
        print(f"Creating MODEL_BACKEND with model: {model_name}")
        MODEL_BACKEND = LitellmModel(
            model=model_name,
            api_key=final_api_key
        )
        print("MODEL_BACKEND created successfully")
        return MODEL_BACKEND

    except Exception as e:
        print(f"Error creating MODEL_BACKEND: {e}")
        sys.exit(1)


def get_tool_name(tool):
    """Get the best-available name for a tool."""
    return (
        getattr(tool, 'name', None) or
        getattr(tool, '__name__', None) or
        getattr(getattr(tool, 'func', None), '__name__', None) or
        str(tool)
    )

def get_tool_description(tool):
    """Get the best-available description for a tool."""
    return (
        getattr(tool, 'description', None) or
        (tool.__doc__.strip() if getattr(tool, '__doc__', None) else None) or
        (tool.func.__doc__.strip() if getattr(getattr(tool, 'func', None), '__doc__', None) else None) or
        'No description'
    )

def get_tool_params(tool):
    """Extract tool parameter names from its JSON schema."""
    schema = getattr(tool, 'params_json_schema', None)
    if not schema:
        return "(...)"

    props = schema.get("properties", {})
    param_names = [par for par in props.keys()]

    return f"({', '.join(param_names)})"

def format_tool(tool):
    name = get_tool_name(tool)
    params = get_tool_params(tool)
    desc = get_tool_description(tool)
    return f"- `{name}{params}`: {desc}"
        
auth_lines = [
    "Your first responsibility is to authenticate the user before fulfilling any requests. "
    "This authentication process has two required steps:\n",

    "1. **Begin by asking the customer for their phone number.**\n"
    "   - Once the phone number is provided, call the tool:\n"
    f"     - {format_tool(send_verification_text)} – This sends a verification code to the customer.\n",

    "2. **Next, ask the customer for the verification code they received.**\n"
    "   - Only after the customer provides a code, call the tool:\n"
    f"     - {format_tool(code_verifier)} – This verifies the customer's identity.\n",

    "**You must not call any tool until you’ve gathered the required information from the user.**\n"
    "Once identity verification is successful, you may continue handling the customer’s requests.\n"
    "---"
]

auth_section = "\n".join(auth_lines)

def load_domain_tools_and_routines():
    """Load all tools and routines for each domain."""
    def remove_duplicate_tools(tools_list):
        seen = set()
        unique = []
        for tool in tools_list:
            name = getattr(tool, "name",
                   getattr(tool, "__name__",
                   getattr(getattr(tool, "func", None), "__name__", str(tool))))
            if name not in seen:
                seen.add(name)
                unique.append(tool)
        return unique

    domain_intents = {
        "banking":            ["update_address", "withdraw_retirement_funds"],
        "flights":            ["book_flight", "cancel_flight"],
        "hospital":           ["process_payment"],
    }

    DOMAIN_ALL_TOOLS = {}
    DOMAIN_ALL_ROUTINES = {}
    INTENT_TOOLS = {}
    INTENT_ROUTINES = {}

    for domain, intents in domain_intents.items():
        tools, routines = [], []
        for intent in intents:
            tools.extend(ALL_TOOL_MAPPING.get(intent, []))
            INTENT_TOOLS[intent] = remove_duplicate_tools(tools)

            if intent in ROUTINE_MAPPING:
                routine = ROUTINE_MAPPING.get(intent)
                INTENT_ROUTINES[intent] = routine.strip()
                routines.append(f"\n=== {intent.upper()} ROUTINE ===\n{routine.strip()}")
        DOMAIN_ALL_TOOLS[domain]   = remove_duplicate_tools(tools)
        DOMAIN_ALL_ROUTINES[domain] = "\n".join(routines)

    print("Loaded domain tools:")
    for domain in domain_intents:
        count = len(DOMAIN_ALL_TOOLS[domain])
        print(f"  {domain.capitalize()}: {count} tool{'s' if count!=1 else ''}")

    return DOMAIN_ALL_TOOLS, DOMAIN_ALL_ROUTINES, INTENT_TOOLS, INTENT_ROUTINES

def format_intents_prompt_section(intent_tools: dict, intent_routines: dict, domain_intents: list[str]) -> str:
    sections = []
    sections.append('You are in charge of authenticating the user and then fulfilling their requests')
    sections.append(
        "You must **always begin your workflow by verifying the customer's identity** "
        "using the following tools:\n\n" + auth_section + "\n"
        "You will now continue with their requests"
    )
    
    if len(domain_intents) == 1:
        header_line = "There is one possible customer intent for the given domain:"
    else:
        header_line = "There are possible customer intents for the given domain:"
    
    sections.append(header_line)
    
    filtered_intents = [intent for intent in intent_tools.keys() if intent in domain_intents]

    intent_lines = []
    for idx, intent in enumerate(filtered_intents, 1):
        intent_lines.append(f"{idx}. **{intent}**")
    sections.append("\n".join(intent_lines))
    
    sections.append("\nEach intent has its own routines and tools:\n")

    for intent in filtered_intents:
        routine = intent_routines.get(intent, "No routine provided").strip()

        tool_lines = [format_tool(tool) for tool in intent_tools.get(intent, [])]

        section = f"""### INTENT: {intent.upper()}
**Routine:**
{routine}

**Tools Available:**
{chr(10).join(tool_lines)}
"""
        sections.append(section)

    return "\n".join(sections)


async def save_dynamic_result_to_customer_data(customer_id: str, domain: str, tool_name: str, result: Any, clean_model_name) -> None:
    """
    Saves the result of a dynamic function call to the customer data JSON file.
    
    Args:
        customer_id (str): The customer ID
        domain (str): The domain (e.g., 'banking', 'flights')
        tool_name (str): Name of the tool that was called
        result (Any): The result of the tool call
    """
    try:
        # Construct paths
        input_file = os.path.join(BASE_DIR, 'test_data', 'customer_data', f'{domain}_utterance.json')
        output_dir = os.path.join(BASE_DIR, 'output', 'dynamic_results', clean_model_name, 'react')
        output_file = os.path.join(output_dir, f'{domain}_utterance.json')
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Determine which file to read from - prefer output file if it exists
        file_to_read = output_file if os.path.exists(output_file) else input_file
        
        # Check if file to read exists
        if not os.path.exists(file_to_read):
            print(f"Warning: Customer data file {file_to_read} does not exist")
            return
            
        # Read existing data
        with open(file_to_read, 'r') as f:
            customer_data = json.load(f)
            
        # Find the customer record
        customer_found = False
        for record in customer_data:
            # Handle different customer ID field names
            record_customer_id = str(record.get('customer_id') or record.get('customerId') or record.get('patientId', ''))
            
            if record_customer_id == str(customer_id):
                # Initialize dynamic_results if it doesn't exist
                if 'dynamic_results' not in record:
                    record['dynamic_results'] = {}
                
                # Convert result to JSON-serializable format
                try:
                    # Test if result is JSON serializable
                    json.dumps(result)
                    serializable_result = result
                except (TypeError, ValueError):
                    # If not serializable, convert to string representation
                    serializable_result = str(result)
                
                # Add the result (this will accumulate, not overwrite)
                record['dynamic_results'][tool_name] = serializable_result
                customer_found = True
                break
                
        if not customer_found:
            print(f"Warning: Customer {customer_id} not found in {file_to_read}")
            return
            
        # Write to output file
        with open(output_file, 'w') as f:
            json.dump(customer_data, f, indent=2)
            
        print(f"Saved dynamic result for tool '{tool_name}' for customer {customer_id} to {output_file}")
            
    except Exception as e:
        print(f"Error saving dynamic result: {e}")
