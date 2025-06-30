from models import AuthenticatedCustomerContext
from typing import Dict, List, Any
import json
from agents import function_tool
import os
import time
import random

customer_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'test_data', 'customer_data', 'flights_utterance.json')


with open(customer_data_path, 'r') as f:
    customer_data = json.load(f)

# Client Information Tools

async def get_customer_frequent_flyer_status(context: AuthenticatedCustomerContext) -> Dict:
    '''
    Retrieves the customer's frequent flyer status.
    
    Args:
        context: The Authenticated Customer Context
    Returns:
        Dict: Dict with the frequent flyer status of the client
    '''
    for customer in customer_data:
        if customer['customer_id'] == context.customer_id:
            frequent_flyer_status = customer['personal_info']['frequent_flyer_status']
            return {'frequent_flyer_status': frequent_flyer_status}

    return {'frequent_flyer_status': None}

    
async def get_passport_info(context: AuthenticatedCustomerContext) -> Dict:
    '''
    Get passport information
    
    Args:
        context: The Authenticated Customer Context
    Returns:
        Dict: Dict including passport number
    '''
    for customer in customer_data:
        if customer['customer_id'] == context.customer_id:
            passport_number = customer['personal_info']['passport_number']
            return {'passport_number': passport_number if passport_number else 'No passport number in system. Must ask customer'}
    
    return {'passport_number': None}


async def get_customer_payment_method(context: AuthenticatedCustomerContext) -> Dict:
    '''
    Retrieves customer payment method from booking information
    
    Args:
        context: The Authenticated Customer Context
    Returns:
        Dict: Dict including payment method information
    '''
    for customer in customer_data:
        if customer['customer_id'] == context.customer_id:
            payment_method = customer['stored_payment_method']
            return {'payment_method': payment_method if payment_method else 'No payment method on file'}
    return {"payment_method": None}


# Execution Tools

@function_tool
async def search_regular_flights(customer_id: int, origin_airport: str, destination_airport: str, departure_date: str) -> List[Dict[str, Any]]:
    '''
    Searches for available flights
    
    Args:
        customer_id: ID of the customer
        origin_airport: Origin airport code
        destination_airport: Destination airport code
        departure_date: Date of departure
        
    Returns:
        Dict: Result of available flights; each dict contains
                    'flight_number', 'departure_time', and 'fare'.
    '''
    for customer in customer_data:
        if customer['customer_id'] == customer_id:
            results = customer.get('flight_search_results') 
            return results
                
    return [
        {'flight_number': 'BA9100', 'departure_time': '13:07', 'fare': 250.00}
    ]

@function_tool
async def search_priority_flights(customer_id: int, origin_airport: str, destination_airport: str, departure_date: str) -> List[Dict[str, Any]]:
    '''
    Searches for available flights
    
    Args:
        customer_id: ID of the customer
        origin_airport: Origin airport code
        destination_airport: Destination airport code
        departure_date: Date of departure
        
    Returns:
        Dict: Result of available flights; each dict contains
                    'flight_number', 'departure_time', and 'fare'.
    '''
    for customer in customer_data:
        if customer['customer_id'] == customer_id:
            results = customer.get('flight_search_results') 
            return results
                
    return [
        {'flight_number': 'BA9100', 'departure_time': '07:23', 'fare': 240.00}
    ]
    

@function_tool
async def check_visa_requirements(origin_airport: str, destination_airport: str) -> Dict:
    '''
    Mandatory check for visa requirements for destination
    
    Args:
        origin_airport: airport code of origin
        destination_airport: airport code of destination
    Returns:
        Dict: Mock result of visa requirement check
    '''
    airport_country_mapping = {
                    # US airports
                    "JFK": "US",
                    "LAX": "US",
                    "ORD": "US",
                    "DFW": "US",
                    "ATL": "US",
                    "SFO": "US",
                    "MIA": "US",
                    "SEA": "US",
                    "BOS": "US",
                    # International airports
                    "LHR": "UK",
                    "CDG": "FR",
                    "NRT": "JP",
                    "SYD": "AU",
                    "HKG": "CN",
                    "SIN": "SG",
                    "DXB": "AE",
                    "AMS": "NL"
                }
                
    # Select origin airport and get its country
    origin_country = airport_country_mapping.get(origin_airport, "Unknown")
    
    # Ensure destination is different from origin
    destination_country = airport_country_mapping.get(destination_airport, "Unknown")
    if origin_country != destination_country:
        return {'visa_required': True, 'details': 'Visa required for entry'}
    else:
        return {'visa_required': False, 'details': 'No visa required'}


@function_tool
async def create_booking(flight_number: str) -> Dict:
    '''
    Creates the flight booking
    
    Args:
        flight_number: Flight number
    Returns:
        Dict: Confirmation of the booking
    '''
    
    return {
        'booking_id': 'BK123456',
        'status': 'Confirmed'
    }


@function_tool
async def create_booking_with_points(flight_number: str) -> Dict:
    '''
    Creates the flight booking
    
    Args:
        flight_number: Flight number
    Returns:
        Dict: Confirmation of the booking
    '''
  
    return {
        'booking_id': 'BK78910',
        'status': 'Confirmed'
    }


@function_tool
async def get_customer_frequent_flyer_status_extra(customer_id: int) -> Dict:
    '''
    Gets saved passenger information
    
    Args:
        customer_id: ID of the customer
    Returns:
        Dict: Dict with the frequent flyer status of the client
    '''
    for customer in customer_data:
        if customer['customer_id'] == customer_id:
            frequent_flyer_status = customer['personal_info']['frequent_flyer_status']
            return {'frequent_flyer_status': frequent_flyer_status}
    
    return {'frequent_flyer_status': None}

    
@function_tool
async def get_passport_info_extra(customer_id: int) -> Dict:
    '''
    Get passport information
    
    Args:
        customer_id: ID of the customer
    Returns:
        Dict: Dict including passport number
    '''
    for customer in customer_data:
        if customer['customer_id'] == customer_id:
            passport_number = customer['personal_info']['passport_number']
            return {'passport_number': passport_number if passport_number else 'No passport number in system. Must ask customer'}
    
    return {'passport_number': None}


@function_tool
async def get_customer_payment_method_extra(customer_id: int) -> Dict:
    '''
    Retrieves customer payment method from booking information
    
    Args:
        customer_id: ID of the customer
    Returns:
        Dict: Dict including payment method information
    '''
    for customer in customer_data:
        if customer['customer_id'] == customer_id:
            payment_method = customer['stored_payment_method']
            return {'payment_method': payment_method if payment_method else 'No payment method on file'}
    return {"payment_method": None}