import openai
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

from utils import extract_info_from_path, load_full_routine, load_customer_data

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from llm_utils import call_open_router_models, extract_json_from_response

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
api_key = os.getenv("OPENROUTER_KEY")


def parse_nested_json_manually(json_str: str) -> dict:
    """
    Manually extract key-value pairs from a malformed JSON string.
    This handles cases where JSON has issues like trailing commas or unescaped quotes.
    
    Args:
        json_str (str): Malformed JSON string
        
    Returns:
        dict: Extracted key-value pairs
    """
    result = {}
    
    # remove trailing commas and clean up
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
    json_str = json_str.strip()
    
    # remove outer braces
    if json_str.startswith('{') and json_str.endswith('}'):
        json_str = json_str[1:-1].strip()
    
    # convert escaped newlines to actual newlines for easier processing
    if '\\n' in json_str:
        json_str = json_str.replace('\\n', '\n')
    
    # remove trailing commas
    json_str = re.sub(r',(\s*\n\s*[}])', r'\1', json_str)
    
    # get key-value pairs 
    pattern = r'"([^"]+)"\s*:\s*"((?:[^"\\]|\\.|"[^",}]*")*)"'
    matches = re.findall(pattern, json_str, re.DOTALL)
    
    for key, value in matches:
        value = value.replace('\\"', '"').strip()
        result[key] = value
    
    return result


def extract_nested_json(response_dict: dict) -> dict:
    """
    Extract and parse nested JSON structures from string fields.
    
    Args:
        response_dict (dict): Dictionary that may contain JSON strings in values
        
    Returns:
        dict: Dictionary with parsed nested JSON structures
    """
    result = response_dict.copy()
    
    for key, value in response_dict.items():
        if isinstance(value, str) and value.strip().startswith('{') and value.strip().endswith('}'):
            try:
                # first normal JSON parsing
                nested_json = json.loads(value)
                if isinstance(nested_json, dict):
                    result.update(nested_json)
                    if key == 'explanation':
                        result.pop(key, None)
            except json.JSONDecodeError:
                try:
                    # try manual parsing
                    nested_json = parse_nested_json_manually(value)
                    if nested_json:
                        result.update(nested_json)
                        if key == 'explanation':
                            result.pop(key, None)
                except Exception:
                    # all parsing fails, keep the original string value
                    continue
                
    return result


def get_formatted_judge_prompt(full_routine: str, customer_data: str, trimmed_routine: str, judge_prompt: str) -> str:
    """
    Formats the judge prompt by replacing placeholders with the actual data.

    Args:
        full_routine (str): The full routine content
        customer_data (str): The customer data
        trimmed_routine (str): The trimmed routine content
        judge_prompt (str): The template for the judge prompt

    Returns:
        str: The formatted judge prompt with all data inserted
    """
    judge_final_prompt = judge_prompt.replace('FULL_ROUTINE', full_routine)
    judge_final_prompt = judge_final_prompt.replace('CUSTOMER_DATA', customer_data)
    judge_final_prompt = judge_final_prompt.replace('TRIMMED_ROUTINE', trimmed_routine)
    return judge_final_prompt
    
async def generate_llm_as_judge_response(judge_prompt: str, routine_file_name: str, model: str, domain: str, intent: str) -> Dict[str, str]:
    """
    Generates a response from the LLM as a judge, processes it, and saves the response as a JSON file.

    This function sends the provided judge prompt to the LLM, receives a response, attempts to parse 
    it as JSON, and saves it to a file named after the `routine_file_name`. If there is an error in
    the response or the JSON decoding, an error message is returned.

    Args:
        judge_prompt (str): The formatted judge prompt to send to the LLM.
        routine_file_name (str): The name of the routine file, used to name the output file.
        model (str): The model used to generate the routine (e.g., 'gpt', 'llama', 'sonnet').
        domain (str): The domain of the routine (e.g., 'IntermediateFlights', 'SimpleBanking').
        intent (str): The intent of the routine (e.g., 'book_flight', 'update_address').

    Returns:
        dict: The parsed JSON response from the LLM, or an error message if there is an issue.
    """
    try:        
        response, time_taken, usage = call_open_router_models(
            prompt=judge_prompt,
            api_key=api_key,
            model="google/gemini-2.0-flash-001")
        
        print(f"Raw LLM Response: {response}...") 
        
        # try getting JSON from response
        assistant_response = extract_json_from_response(response)

        parsed_response = None
        
        # 1st try: Parse the extracted response directly
        try:
            parsed_response = json.loads(assistant_response)
            
            # Extract nested JSON structures if present
            parsed_response = extract_nested_json(parsed_response)
            
        except json.JSONDecodeError as e:
            # 2nd try: Look for JSON-like content manually
            try:
                # find JSON content between { and }
                start_idx = assistant_response.find('{')
                end_idx = assistant_response.rfind('}') + 1
                
                if start_idx != -1 and end_idx > start_idx:
                    json_content = assistant_response[start_idx:end_idx]
                    parsed_response = json.loads(json_content)
                    
                    # get nested JSON structures if present
                    parsed_response = extract_nested_json(parsed_response)
                else:
                    raise json.JSONDecodeError("No JSON structure found", assistant_response, 0)
                    
            except json.JSONDecodeError:
                # 3rd try: create a structured response from the text
                print("Could not parse JSON, creating structured response from text...")
                # get score and explanation manually if possible
                score = "1"  # Default score
                explanation = assistant_response
                
                # try to find score in the text
                if "score" in assistant_response.lower():
                    score_match = re.search(r'"?(?:relevance_|completeness_)?score"?\s*:?\s*"?([123])"?', assistant_response, re.IGNORECASE)
                    if score_match:
                        score = score_match.group(1)
                
                parsed_response = {
                    "score": score,
                    "explanation": explanation,
                    "note": "JSON parsing failed, manual extraction used"
                }

        #add metadata to the response
        parsed_response["model"] = model
        parsed_response["domain"] = domain
        parsed_response["intent"] = intent

        base_dir = Path(__file__).resolve().parent.parent
        output_dir = base_dir / "output" / "judge_trimmed_routine" / model / domain
        
        output_dir.mkdir(parents=True, exist_ok=True) 

        output_file = output_dir / f"{routine_file_name}_judge.json"

        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(parsed_response, file, ensure_ascii=False, indent=4)
        
        print(f"Response saved to: {output_file}")

        return parsed_response

    except Exception as e:
        print(f'Error: {e}')
        error_response = {
            "error": f"Error with LLM response: {e}",
            "score": "1",
            "explanation": f"Failed to process response due to error: {e}",
            "model": model,
            "domain": domain,
            "intent": intent
        }
        return error_response

async def process_routines_in_directory():
    """
    Processes each routine file in the 'evaluation/trimmed_routines/' directory, generates a judge response, 
    and saves the results.

    This function reads each routine file in the specified directory, extracts the domain, intent, and customer_id,
    loads the corresponding full routine and customer data, formats a judge prompt with all the information,
    and then generates a response from the LLM using the formatted prompt. The response is saved as a JSON file
    in the 'output' directory.

    Returns:
        None
    """
    try:
        base_dir = Path(__file__).parent.parent / 'output' / 'trimmed_routines'
        print(f"Processing routines from: {base_dir}")
        
        all_txt_files = list(base_dir.rglob("*.txt"))
    
        #group files by their leaf directory
        dir_to_files = defaultdict(list)
        for file in all_txt_files:
            if file.parent != base_dir:  # ensures it's in a subdirectory
                dir_to_files[file.parent].append(file)
    
        sampled_files = []
        for dir_path, files in dir_to_files.items():
            # sample_size = max(1, int(len(files) * 0.1))  # if we want to just sample 10% for testing
            # sampled = random.sample(files, sample_size)
            sampled_files.extend(sampled)

        print(f"Selected {len(sampled_files)} files for processing.")

        #loop through each file
        for routine_file in sampled_files:
            if ".ipynb_checkpoints" in routine_file.parts or "checkpoint" in routine_file.name:
                continue
            print(f'Processing routine: {routine_file.stem}')
            
            #get domain, intent, model, and customer_id from the file path
            info = extract_info_from_path(routine_file)
            domain = info['domain']
            intent = info['intent']
            model = info['model']
            customer_id = info['customer_id']
            customer_data_file = info['customer_data_file']
            
            print(f"Model: {model}, Domain: {domain}, Intent: {intent}, Customer ID: {customer_id}")
            
            with open(routine_file, 'r', encoding='utf-8') as file:
                trimmed_routine = file.read()
            
            full_routine = load_full_routine(domain, intent)
            customer_data = load_customer_data(customer_id, model, intent, customer_data_file)
            
            formatted_prompt = get_formatted_judge_prompt(
                full_routine, customer_data, trimmed_routine, judge_prompt
            )

            print(f"\033[34m{formatted_prompt}\033[0m")
            
            await generate_llm_as_judge_response(formatted_prompt, routine_file.stem, model, domain, intent)

    except Exception as e:
        print(f'Error processing routine files: {e}')

if __name__ == "__main__":
    asyncio.run(process_routines_in_directory())