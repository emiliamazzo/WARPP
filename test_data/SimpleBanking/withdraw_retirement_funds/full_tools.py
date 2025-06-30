from models import AuthenticatedCustomerContext
from typing import Dict
import json
from agents import function_tool
import os

customer_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'test_data', 'customer_data', 'banking_utterance.json')

with open(customer_data_path, 'r') as f:
    customer_data = json.load(f)


@function_tool
async def process_retirement_withdrawal(customer_id:int, withdrawal_amount: float) -> Dict:
    '''
    Processes the retirement account withdrawal
    
    Args:
        customer_id: The customer ID
        withdrawal_amount: The amount to be withdrawn
    Returns:
        Dict: Dict indicating the success of the transaction
    '''
    # Simulated processing logic
    for customer in customer_data:
        if customer['customer_id'] == customer_id:
            remaining_balance = customer['account_balance'] - withdrawal_amount
            return {
                'status': 'Success',
                'remainingBalance': remaining_balance
            }

async def check_withdrawal_eligibility(context: AuthenticatedCustomerContext) -> Dict:
    '''
    Checks if withdrawal is allowed for the given customerId
    
    Args:
        context: The Authenticated Customer Context
    Returns:
        Dict: Dict indicating eligibility status
    '''
    eligible_types = ['ROTH_IRA', 'TRADITIONAL_IRA']
    for customer in customer_data:
        if customer['customer_id'] == context.customer_id:
            account_type = customer['account_type']
    print(account_type)
    if account_type in eligible_types:
        return {'isEligible': True}
    else:
        return {'isEligible': False}

    
@function_tool
async def check_withdrawal_eligibility_extra(customer_id: int) -> Dict:
    '''
    Checks if withdrawal is allowed for the given customerId
    
    Args:
        customer_id: The customer ID
    Returns:
        Dict: Dict indicating eligibility status
    '''
    eligible_types = ['ROTH_IRA', 'TRADITIONAL_IRA']
    for customer in customer_data:
        if customer['customer_id'] == customer_id:
            account_type = customer['account_type']
    print(account_type)
    if account_type in eligible_types:
        return {'isEligible': True}
    else:
        return {'isEligible': False}