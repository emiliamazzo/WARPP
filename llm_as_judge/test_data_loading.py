import sys
import os
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm_as_judge.judge_run import extract_info_from_path, load_full_routine, load_customer_data, get_formatted_judge_prompt
from llm_as_judge.instructions import judge_prompt

def test_data_loading():
    """Test function to verify data loading works correctly."""
    
    # Test with a sample routine file path
    base_dir = Path(__file__).parent.parent / 'output' / 'trimmed_routines'
    
    # Find a sample file to test with
    sample_files = list(base_dir.rglob("*.txt"))
    
    if not sample_files:
        print("No sample files found!")
        return
    
    sample_file = sample_files[0]
    print(f"Testing with file: {sample_file}")
    
    # Test extract_info_from_path
    info = extract_info_from_path(sample_file)
    print(f"Extracted info: {info}")
    
    domain = info['domain']
    intent = info['intent']
    customer_id = info['customer_id']
    customer_data_file = info['customer_data_file']
    
    # Test load_full_routine
    print(f"\nLoading full routine for domain: {domain}, intent: {intent}")
    full_routine = load_full_routine(domain, intent)
    print(f"Full routine (first 200 chars): {full_routine[:200]}...")
    
    # Test load_customer_data
    print(f"\nLoading customer data for file: {customer_data_file}, customer_id: {customer_id}")
    customer_data = load_customer_data(customer_data_file, customer_id)
    print(f"Customer data (first 200 chars): {customer_data[:200]}...")
    
    # Test reading trimmed routine
    print(f"\nReading trimmed routine...")
    with open(sample_file, 'r', encoding='utf-8') as file:
        trimmed_routine = file.read()
    print(f"Trimmed routine (first 200 chars): {trimmed_routine[:200]}...")
    
    # Test formatting the prompt
    print(f"\nFormatting judge prompt...")
    formatted_prompt = get_formatted_judge_prompt(full_routine, customer_data, trimmed_routine, judge_prompt)
    print(f"Formatted prompt (first 500 chars): {formatted_prompt[:500]}...")
    
    print("\nTest completed successfully")

if __name__ == "__main__":
    test_data_loading() 