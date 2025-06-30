import openai
from openai import OpenAI
import os
from prompt import first_utterance_generator_prompt
import argparse

def generate_utterances(complexity: str):
    """
    Generate sample user utterances for a given task complexity level 
    using OpenAI's GPT-4o model and save them to a file.
    """
                                   
    if complexity == 'simple':
        intent1, intent2, domain = 'Update Address', 'Withdraw Retirement Funds', 'Banking'
    if complexity == 'intermediate':
        intent1, intent2, domain = 'Book Flight', 'Cancel Flight', 'Flights'        
    if complexity == 'complex':
        intent1, intent2, domain = 'Book Appointment', 'Process Payment', 'Hospital'
    
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    if openai.api_key is None:
        raise ValueError("Missing OpenAI API key. Set the OPENAI_API_KEY environment variable.")
    
    final_prompt = first_utterance_generator_prompt.replace('{INTENT1}', intent1)\
                                                   .replace('{INTENT2}', intent2)\
                                                   .replace('{DOMAIN}', domain)
    if complexity == 'intermediate':
        final_prompt += 'NEVER mention any locations in your utterances. Do not include cities or airports.'
    
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    response = client.responses.create(
        model="gpt-4o",
        input=final_prompt
    )
    
    print(response.output_text)
    
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, f"{complexity}.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(response.output_text)
    print(f"Output saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate customer service first utterances from intents.")
    parser.add_argument("--complexity", choices=["simple", "intermediate", "complex"])

    args = parser.parse_args()
    generate_utterances(args.complexity)