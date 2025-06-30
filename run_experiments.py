import subprocess
import sys
import os
from itertools import product

MODELS = [
    "openrouter/openai/gpt-4o",
    "openrouter/meta-llama/llama-3-70b-instruct", 
    # "anthropic/claude-3-5-sonnet-20240620"
]

# API Keys from environment variables
def get_api_keys():
    """Get API keys from environment variables."""
    return {
        "openrouter/openai/gpt-4o": os.getenv("OPENROUTER_KEY", ""),
        "openrouter/meta-llama/llama-3-70b-instruct": os.getenv("OPENROUTER_KEY", ""),
        "anthropic/claude-3-5-sonnet-20240620": os.getenv("ANTHROPIC_API_KEY", "")
    }

INTENTS = ["update_address", "withdraw_retirement_funds"]
DOMAIN = "banking" 
PROMPT_TYPE = "Basic"
PARALLELIZATION_OPTIONS = [True, False]  # True = --parallelization, False = no flag

def run_experiment(model, intent, parallelization, api_key):
    """Run a single experiment with the given parameters."""
    
    cmd = [
        "python", "app.py",
        f"--domains={DOMAIN}",
        f"--intent={intent}",
        f"--prompt={PROMPT_TYPE}",
        f"--model={model}",
        f"--api_key={api_key}"
    ]
    #for react
    # cmd = [
    #     "python", "react/react_agent.py",
    #     f"--domains={DOMAIN}",
    #     f"--intent={intent}",
    #     # f"--prompt={PROMPT_TYPE}",
    #     f"--model={model}",
    #     f"--api_key={api_key}"
    # ]
    
    if parallelization:
        cmd.append("--parallelization")
    
    parallel_str = "parallel" if parallelization else "non-parallel"
    print(f"\n{'='*80}")
    print(f"Running: Model={model}, Intent={intent}, Mode={parallel_str}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True, check=True)
        print(f"SUCCESS: {model} - {intent} - {parallel_str}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"FAILED: {model} - {intent} - {parallel_str}")
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"ERROR: {model} - {intent} - {parallel_str}")
        print(f"Unexpected error: {e}")
        return False

def main():
    """Run all experiment combinations."""
    print("Starting flight booking/cancellation experiments...")
    print(f"Models: {len(MODELS)}")
    print(f"Intents: {len(INTENTS)}")
    print(f"Parallelization options: {len(PARALLELIZATION_OPTIONS)}")
    print(f"Total experiments: {len(MODELS) * len(INTENTS) * len(PARALLELIZATION_OPTIONS)}")
    
    # Get API keys from environment
    API_KEYS = get_api_keys()
    
    # Verify API keys are set
    missing_keys = []
    for model in MODELS:
        if not API_KEYS.get(model):
            missing_keys.append(model)
    
    if missing_keys:
        print(f"\n⚠️  WARNING: Missing API keys for: {missing_keys}")
        print("Please set the following environment variables:")
        if any("openrouter" in model for model in missing_keys):
            print("  export OPENROUTER_KEY='your_openrouter_key_here'")
        if any("anthropic" in model for model in missing_keys):
            print("  export ANTHROPIC_API_KEY='your_anthropic_key_here'")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Exiting...")
            return
    
    successful = 0
    failed = 0
    
    # run all combinations
    for model, intent, parallelization in product(MODELS, INTENTS, PARALLELIZATION_OPTIONS):
        api_key = API_KEYS.get(model, "")
        
        success = run_experiment(model, intent, parallelization, api_key)
        if success:
            successful += 1
        else:
            failed += 1


if __name__ == "__main__":
    main() 