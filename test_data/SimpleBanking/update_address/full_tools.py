from models import AuthenticatedCustomerContext
from typing import Dict, Any
import json
from agents import function_tool
import os

customer_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'test_data', 'customer_data', 'banking_utterance.json')

with open(customer_data_path, 'r') as f:
    customer_data = json.load(f)


@function_tool
async def validate_address(street: str, city: str, state: str, zip_code: str, country: str) -> Dict:
    '''
    Validates and standardizes the input address
    
    Args:
        street: Street address
        city: City name
        state: State code
        zip_code: ZIP code
        country: Country code
    Returns:
        Dict with validation result and standardized address
    '''
    return {
        'isValid': True,
        'standardizedAddress': {
            'street': street.upper(),
            'city': city.upper(),
            'state': state.upper(),
            'zipCode': zip_code,
            'country': country.upper(),
            'zipPlus4': '0000'
        },
        'addressId': 'addr789'
    }


@function_tool
async def update_address(customer_id: int, street: str, city: str, state: str, zip_code: str, country: str) -> Dict:
    '''
    Updates client's address in the system
    
    Args:
        customer_id: ID of the customer
        street: Street address
        city: City name
        state: State code
        zip_code: ZIP code
        country: Country code
    Returns:
        Dict indicating success
    '''
    # Simulate address update
    address = {
        'street': street.upper(),
        'city': city.upper(),
        'state': state.upper(),
        'zipCode': zip_code,
        'country': country.upper()
    }
    
    return {
        'success': True,
        'message': 'Address updated successfully',
        'customer_id': customer_id,
        'updated_address': address
    }

async def get_account_type(context: AuthenticatedCustomerContext) -> Dict:
    '''
    Get account type and ownership information
    
    Args:
        context: The Authenticated Customer Context
    Returns:
        Dict: Dict including account type info
    '''
    # for customer in customer_data['banking']: 
    for customer in customer_data: 
        if customer['customer_id'] == context.customer_id:
            return {
                'account_type': customer['account_type'],
                'client_level': customer['client_level']

            }
    return {'account_type': {}}



@function_tool
async def get_account_type_extra(customer_id: int) -> Dict:
    '''
    Get account type and ownership information
    
    Args:
        customer_id: ID of the customer

    Returns:
        Dict: Dict including account type info
    '''
    # for customer in customer_data['banking']:

    for customer in customer_data:
        if customer['customer_id'] == customer_id:
            return {
                'account_type': customer['account_type'],
                'client_level': customer['client_level']
            }
    return {'account_type': {}}

@function_tool
async def apply_address_hold(customer_id: int) -> Dict:
    '''
    Applies a hold period to the account after address change
    
    Args:
        customer_id: ID of the customer
    Returns:
        Dict indicating success
    '''
    # Simulate applying address hold
    return {
        'success': True,
        'message': 'Address hold applied successfully',
        'customer_id': customer_id
    }
