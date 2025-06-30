INTENT_MAPPING = {
    "update_address_intent": {
        "intent": "update_address",
        "client_info_tools": ['get_account_type'],
        "client_info_tools_extra": ['get_account_type_extra'],
        "execution_tools": ['validate_address', 'apply_address_hold', 'update_address']
    },
    "withdraw_retirement_funds_intent": {
        "intent": "withdraw_retirement_funds",
        "client_info_tools": ['check_withdrawal_eligibility'],
        "client_info_tools_extra": ['check_withdrawal_eligibility_extra'],
        "execution_tools": [ 'process_retirement_withdrawal']
    },
}
