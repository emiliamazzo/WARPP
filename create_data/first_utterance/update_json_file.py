import json
import re
import argparse


def process_customers(complexity):
    if complexity == 'simple':
        output_folder_domain = 'banking'
    elif complexity == 'intermediate':
        output_folder_domain = 'flights'
    elif complexity == 'complex':
        output_folder_domain = 'hospital'


    intent_file = f"output/{complexity}.txt"
    customer_file = f"../../test_data/customer_data/{output_folder_domain}.json"
    output_file = f"../../test_data/customer_data/{output_folder_domain}_utterance.json"


    with open(intent_file, "r") as f:
        lines = f.readlines()
    
    intent_examples = {}
    current_intent = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # catch intent opening line
        intent_match = re.match(r"\*\*Intent:\s*(.+?)\*\*", line)
        
        if intent_match:
            # normalize intent name to match agent_sequence values
            intent_name = intent_match.group(1).strip().lower().replace(" ", "_")
            current_intent = intent_name
            intent_examples[current_intent] = []
        elif current_intent:
            # add each utterance line under the current intent
            intent_examples[current_intent].append(line)
    
    # load customer json
    with open(customer_file, "r") as f:
        customers = json.load(f)
    
    # for each intent, keep a counter to assign utterances in order
    counters = {intent: 0 for intent in intent_examples}
    
    # iterate over customers and assign the first_utterance field
    for record in customers:
        intent = record["agent_sequence"][0]
        examples = intent_examples.get(intent, [])
        idx = counters.get(intent, 0)
        if examples:
            utterance_idx = idx % len(examples) 
            record.setdefault("user_provided_info", {})["first_utterance"] = examples[utterance_idx]
            counters[intent] = idx + 1
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(customers, f, indent=2, ensure_ascii=False)
    
    print("Processed {} customers.".format(len(customers)))
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assign utterances to customers based on intent.")
    parser.add_argument("--complexity", type=str, required=True, choices=["simple", "intermediate", "complex"])
    args = parser.parse_args()
    
    process_customers(args.complexity)
