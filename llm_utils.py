from openai import OpenAI
from datetime import datetime
from typing import Tuple, Dict
import time
import re

def call_open_router_models(
    prompt: str,
    api_key: str,
    model: str = "meta-llama/llama-4-maverick:free",
) -> Tuple[str, float, Dict[str,int]]:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    max_retries = 2
    backoff_secs = 10
    last_error = None
    
    for attempt in range(1, max_retries+1):
        start = datetime.now()
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        end = datetime.now()
        time_taken = (end - start).total_seconds()

        # 1) if OpenRouter reports an error payload
        err = getattr(completion, "error", None)
        if err is not None:
            code = err.get("code")
            msg  = err.get("message", "Unknown error")
            last_error = (code, msg)

            # on rate‑limit 429, retry
            if code == 429 and attempt < max_retries:
                wait = backoff_secs * attempt
                print(f"\033[91m❌❌❌❌❌ [WARN] rate‑limit hit, retry {attempt}/{max_retries} in {wait}s ❌❌❌❌❌\033[0m")
                time.sleep(wait)
                continue

            # non‑retryable or final retry: return the error as trajectory
            error_str = f"Error {code}: {msg}"
            return error_str, time_taken, {"prompt_tokens":0,"completion_tokens":0,"total_tokens":0}

        # 2) sanity‑check choices
        choices = getattr(completion, "choices", None)
        if not choices or not getattr(choices[0], "message", None):
            last_error = ("NoChoices", "No response from model")
            break

        # 3) pull out usage safely
        usage = getattr(completion, "usage", None) or {}
        def safe_int(x): return x or 0
        usage_dict = {
            "prompt_tokens":     safe_int(getattr(usage, "prompt_tokens", 0)),
            "completion_tokens": safe_int(getattr(usage, "completion_tokens", 0)),
            "total_tokens":      safe_int(getattr(usage, "total_tokens", 0)),
        }

        return (
            choices[0].message.content,
            time_taken,
            usage_dict
        )


def extract_json_from_response(response: str) -> str:
    # Try to extract content inside code fences
    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
    
    if code_block_match:
        return code_block_match.group(1)
    return response 