INTENT_MAPPING = {
    "cancel_flight_intent": {
        "intent": "cancel_flight",
        "client_info_tools": ['get_booking_details', 'get_customer_loyalty_info'],
        "client_info_tools_extra": ['get_booking_details_extra', 'get_customer_loyalty_info_extra'],
        "execution_tools": ['check_cancellation_blockers', 'calculate_cancellation_fee', 'cancel_flight', 'process_refund', 'issue_travel_credit']
    },
    "book_flight_intent": {
        "intent": "book_flight",
        "client_info_tools": ['get_customer_frequent_flyer_status', 'get_passport_info', 'get_customer_payment_method'],
        "client_info_tools_extra": ['get_customer_frequent_flyer_status_extra', 'get_passport_info_extra', 'get_customer_payment_method_extra'],
        "execution_tools": ['search_regular_flights', 'search_priority_flights', 'check_visa_requirements', 'create_booking', 'create_booking_with_points', 'add_special_services']
    },
}
