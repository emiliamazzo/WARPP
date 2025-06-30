from typing import Dict
from collections import defaultdict
import random
from instructions import judge_prompt
from dotenv import load_dotenv
from pathlib import Path
import json
import asyncio
import os, sys
import re

def extract_info_from_path(routine_file_path: Path) -> Dict[str, str]:
    """
    Extracts domain, intent, model, and customer_id from the trimmed routine file path.
    
    Args:
        routine_file_path (Path): Path to the trimmed routine file
        
    Returns:
        Dict[str, str]: Dictionary containing domain, intent, model, and customer_id
    """
    # exaple path: output/trimmed_routines/gpt/parallel_Basic/book_flight/10122843_routine.txt
    parts = routine_file_path.parts
    
    # get model (third from end: gpt, llama, sonnet, etc.)
    model = parts[-4]  # e.g., "gpt"
    
    # get intent (second to last directory)
    intent = parts[-2]  # e.g., "book_flight"
    
    # get customer_id from filename
    customer_id = routine_file_path.stem.replace('_routine', '')  # e.g., "10122843"
    
    # intent to actual domain directories and customer data files
    intent_to_config = {
        'book_flight': {'domain': 'IntermediateFlights', 'customer_data': 'flights'},
        'cancel_flight': {'domain': 'IntermediateFlights', 'customer_data': 'flights'},
        'book_appointment': {'domain': 'ComplexHospital', 'customer_data': 'hospital'},
        'process_payment': {'domain': 'ComplexHospital', 'customer_data': 'hospital'},
        'update_address': {'domain': 'SimpleBanking', 'customer_data': 'banking'},
        'withdraw_retirement_funds': {'domain': 'SimpleBanking', 'customer_data': 'banking'},
    }
    
    config = intent_to_config.get(intent, {'domain': intent, 'customer_data': intent})
    
    return {
        'domain': config['domain'],
        'intent': intent,
        'model': model,
        'customer_id': customer_id,
        'customer_data_file': config['customer_data']
    }



def load_full_routine(domain: str, intent: str) -> str:
    """
    Loads the full routine from the corresponding workflow file.
    
    Args:
        domain (str): The domain name
        intent (str): The intent name
        
    Returns:
        str: The full routine content
    """
    try:
        workflow_file = Path(__file__).parent.parent / 'test_data' / domain / intent / 'full_workflow.py'
        
        if workflow_file.exists():
            with open(workflow_file, 'r', encoding='utf-8') as file:
                content = file.read()
                triple_quote_pattern = re.compile(r"'''(.*?)'''|\"\"\"(.*?)\"\"\"", re.DOTALL)
                match = triple_quote_pattern.search(content)
                
                if match:
                    # extract from group 1 or 2 depending on which matched
                    extracted = match.group(1) if match.group(1) is not None else match.group(2)
                    return extracted.strip()
                else:
                    return "No triple-quoted workflow content found."
        else:
            return f"Workflow file not found for domain: {domain}, intent: {intent}"
    except Exception as e:
        return f"Error loading full routine: {e}"


def load_customer_data(customer_id: str, model, intent, domain) -> str:
    """
    Loads the customer data from the corresponding JSON file.
    
    Args:
        model (str): The name of the model used to generate the customer data.
        intent (str): The specific intent associated with the customer interaction.
        customer_id (str): The ID of the customer to retrieve.

    Returns:
        str: A JSON-formatted string with the customer's ID and their `info_gathering_results`,
             or an error message if the file is missing or the customer is not found.
    """
    try:
        customer_file = Path(__file__).parent.parent / 'output' / 'dynamic_results' / model / 'parallel' / 'Basic' / f'{domain}_utterance.json'
        
        if customer_file.exists():
            with open(customer_file, 'r', encoding='utf-8') as file:
                all_customers = json.load(file)
                
                for customer in all_customers:
                    if str(customer.get('customer_id')) == customer_id:
                        result = {
                            "customer_id": customer.get("customer_id"),
                            "information_available": customer.get("info_gathering_results", {})
                        }
                        return json.dumps(result, indent=2)
                
                print(f"Warning: Customer {customer_id} not found in {customer_file}")
                return f"Customer {customer_id} not found in {customer_file} data"
        else:
            print(f"Warning: Customer data file not found at {customer_file}")
            return f"Customer data file not found for: {customer_file}"
    
    except Exception as e:
        print(f"Error loading customer data: {e}")
        return f"Error loading customer data: {e}"