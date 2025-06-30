from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
EXP_TYPE = "basic_react"
OUTPUT_ROOT = BASE_DIR / "output"
REACT_TRAJECTORY = OUTPUT_ROOT / "trajectory"
DOMAIN_INTENTS = {
    "banking": ["update_address", "withdraw_retirement_funds"],
    "flights": ["book_flight", "cancel_flight"],
    "hospital": ["process_payment"],
}
