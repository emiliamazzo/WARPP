from models import AuthenticatedCustomerContext
from typing import Dict
import json
from agents import function_tool
import os
import random

customer_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'test_data', 'customer_data', 'flights_utterance.json')


with open(customer_data_path, 'r') as f:
    customer_data = json.load(f)

# Client Information Tools

async def get_booking_details(context: AuthenticatedCustomerContext) -> Dict:
    """
    Retrieves flight booking information for the customer.

    Args:
        context: The authenticated customer context containing the customer ID.

    Returns:
        Dict: A dictionary containing the customer's booking information.
    """
    return_dict = {}
    for customer in customer_data:
        if customer['customer_id'] == context.customer_id:
            if 'booking_info' in customer:
                return_dict['booking_information'] = customer['booking_info']
            if 'stored_payment_method' in customer:
                return_dict['stored_payment_method'] = customer['stored_payment_method']
    return return_dict   

async def get_customer_loyalty_info(context: AuthenticatedCustomerContext) -> Dict:
    """
    Retrieves the loyalty status and points for the customer.

    Args:
        context: The authenticated customer context containing the customer ID.

    Returns:
        Dict: A dictionary containing the customer's loyalty points and frequent flyer status.
    """

    for customer in customer_data:
        if customer['customer_id'] == context.customer_id:
            loyalty_points = customer['personal_info']['loyalty_points']
            frequent_flyer_status = customer['personal_info']['frequent_flyer_status']
            return {'loyalty_points': loyalty_points,
                    'frequent_flyer_status': frequent_flyer_status}
            
    return {'frequent_flyer_status': 'Error Retrieving loyalty information'}
    

# Execution Tools

@function_tool
async def check_cancellation_blockers(booking_id: str) -> Dict:
    """
    Simulates a live check for non–time-based barriers to cancellation.

    Args:
      booking_id (str): The booking reference.

    Returns:
      Dict: { "status": one of:
        - "eligible"                   # you can cancel
        - "fare_rule_blackout"         # cancellation is blocked by a blackout window
        - "vendor_lock"                # ticket issued by a partner with its own lock
        - "system_outage"              # cancellations are temporarily disabled
        - "api_failure"                # transient system error
      }
    """
    status = random.choices(
        [
          "eligible",
          "fare_rule_blackout",
          "vendor_lock",
          "system_outage",
          "api_failure"
        ],
        weights=[0.7, 0.05, 0.15, 0.05, 0.05],
        k=1
    )[0]
    return {"status": status}
    

@function_tool
async def calculate_cancellation_fee(customer_id: int, booking_id: str) -> Dict:
    """
    Calculates the cancellation fee for a specific flight booking.

    Args:
        customer_id (int): The ID of the customer.
        booking_id (str): The booking ID of the flight.

    Returns:
        Dict: A dictionary containing the booking ID, amount paid, and cancellation fee.
    """
    for customer in customer_data:
        if customer['customer_id'] == customer_id:
            booking = customer.get('booking_info', [])

            amount_paid = booking.get('amount_paid')

            cancellation_fee = round(amount_paid * 0.10, 2)

            return {
                "booking_id": booking_id,
                "amount_paid": amount_paid,
                "cancellation_fee": cancellation_fee
            }
    
    return {'cancellation_fee': 'Error Retrieving Cancellation Fee for Current Booking'}

    

@function_tool
async def cancel_flight(booking_id: str) -> Dict:
    """
    Processes a flight cancellation request.

    Args:
        booking_id (str): The booking ID of the flight to be canceled.

    Returns:
        Dict: A dictionary confirming the cancellation status and booking ID.
    """
    # Simulating flight cancellation
    return {
        'cancellation_status': 'Success',
        'booking_id': booking_id
    }


@function_tool
async def process_refund(customer_id: int, booking_id: str, payment_method: str, cancellation_fee: float) -> Dict:
    """
    Processes a refund to the original payment method after flight cancellation.

    Args:
        customer_id (int): The ID of the customer.
        booking_id (str): The booking ID of the canceled flight.
        payment_method (str): The payment method used for the original booking.
        cancellation_fee (float): The cancellation fee to be deducted from the refund.

    Returns:
        Dict: A dictionary confirming the refund status, refund amount, and currency.
    """
    for customer in customer_data:
        if customer['customer_id'] == customer_id:
            booking = customer.get('booking_info', [])

            amount_paid = booking.get('amount_paid')
            total_refunded = amount_paid - cancellation_fee
            
            return {
                'refund_status': 'Processed',
                'refund_amount': total_refunded,
                'currency': 'USD'
            }
    return {'refund_status': 'Failed'}


@function_tool
async def issue_travel_credit(customer_id: int,  booking_id: str, cancellation_fee: float) -> Dict:
    """
    Issues a travel credit for future use instead of a refund.

    Args:
        customer_id (int): The ID of the customer.
        booking_id (str): The booking ID of the canceled flight.
        cancellation_fee (float): The cancellation fee to be deducted from the travel credit.

    Returns:
        Dict: A dictionary confirming the credit status, awarded amount, and currency.
    """
    for customer in customer_data:
        if customer['customer_id'] == customer_id:
            booking = customer.get('booking_info', [])

            amount_paid = booking.get('amount_paid')
            total_refunded = amount_paid - cancellation_fee
            
            return {
                'credit_status': 'Processed',
                'amount_awarded': total_refunded,
                'currency': 'USD'
            }
    return {'refund_status': 'Failed'}


@function_tool
async def get_booking_details_extra(customer_id: int) -> Dict:
    '''
    Retrieves flight booking information for the customer.

    Args:
        context: The authenticated customer context containing the customer ID.

    Returns:
        Dict: A dictionary containing the customer's booking information.
    '''

    return_dict = {}
    for customer in customer_data:
        if customer['customer_id'] == customer_id:
            if 'booking_info' in customer:
                return_dict['booking_information'] = customer['booking_info']
            if 'stored_payment_method' in customer:
                return_dict['stored_payment_method'] = customer['stored_payment_method']
    return return_dict

@function_tool
async def get_customer_loyalty_info_extra(customer_id: int) -> Dict:
    '''
    Retrieves the loyalty status and points for the customer.

    Args:
        context: The authenticated customer context containing the customer ID.

    Returns:
        Dict: A dictionary containing the customer's loyalty points and frequent flyer status.
    '''
    for customer in customer_data:
        if customer['customer_id'] == customer_id:
            loyalty_points = customer['personal_info']['loyalty_points']
            frequent_flyer_status = customer['personal_info']['frequent_flyer_status']
            return {'loyalty_points': loyalty_points,
                    'frequent_flyer_status': frequent_flyer_status}
            
    return {'frequent_flyer_status': 'Error Retrieving loyalty information'}