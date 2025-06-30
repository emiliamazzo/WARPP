import json

routine_data = {
    "book_flight": json.load(open("../test_data/IntermediateFlights/book_flight/full_workflow.json")),
    "cancel_flight": json.load(open("../test_data/IntermediateFlights/cancel_flight/full_workflow.json"))
}



required_fields = ['agent_sequence',
                   'customer_id', 
                   "booking_info['booking_id']",
                   "booking_info['cancellation_allowed']",
                   "booking_info['is_refundable']",
                   "booking_info['purchased_insurance']",
                   "booking_info['amount_paid']",
                   'stored_payment_method',
                   "personal_info['frequent_flyer_status']", 
                   "personal_info['passport_number']",
                   "personal_info['loyalty_points']",
                   "flight_search_results",
                   "user_provided_info['origin_airport']", 
                   "user_provided_info['destination_airport']", 
                   "user_provided_info['departure_date']", 
                   "user_provided_info['preferred_flight_number']",
                   "user_provided_info['authenticator_code']",
                   "user_provided_info['mobile_phone_number']",
                   "user_provided_info['flight_type']",                   
                   "contact_info['mobile_phone_number']",
                   "authenticator_api['authenticator_code']"
]


flight_search_results = {
    "{'flight_number': 'BA9100', 'departure_time': '07:23', 'fare': 240.00}": 0.2,
    "{'flight_number': 'BA9100', 'departure_time': '09:15', 'fare': 310.00}": 0.2,
    "{'flight_number': 'BA9100', 'departure_time': '12:45', 'fare': 280.00}": 0.2,
    "{'flight_number': 'BA9100', 'departure_time': '15:00', 'fare': 265.00}": 0.2,
    "{'flight_number': 'BA9100', 'departure_time': '18:30', 'fare': 295.00}": 0.2
}

origin_options = {
    "JFK": 0.2,
    "LAX": 0.2,
    "BOS": 0.2,
    "CDG": 0.2,
    "DXB": 0.2
}

destination_options = {
    "LHR": 0.2,
    "NRT": 0.2,
    "SYD": 0.2,
    "ATL": 0.2,
    "SEA": 0.2
}

booking_ids = {
    "BK001XZ9": 0.1,
    "BK002YT3": 0.1,
    "BK003MA7": 0.1,
    "BK004PQ4": 0.1,
    "BK005LE8": 0.1,
    "BK006RU1": 0.1,
    "BK007SN5": 0.1,
    "BK008CV2": 0.1,
    "BK009JD6": 0.1,
    "BK010KF0": 0.1
}

passport_numbers = {
    "P1234567": 0.1,
    "P2345678": 0.1,
    "P3456789": 0.1,
    "P4567890": 0.1,
    "P5678901": 0.1,
    "P6789012": 0.1,
    "P7890123": 0.1,
    "P8901234": 0.1,
    "P9012345": 0.1,
    "P0123456": 0.1
}

template = {
'agent_sequence': {'book_flight': 50, 'cancel_flight': 50},
'customer_id': {'random_int(10000000, 99999999)': 1.0}, 
"contact_info['mobile_phone_number']": {'random_int(1000000000, 9999999999)': 1.0},
"authenticator_api['authenticator_code']": {'random_int(100000, 999999)': 1.0},
"booking_info['booking_id']": booking_ids,
"booking_info['cancellation_allowed']": {'true': 0.8, 'false': 0.2},
"booking_info['is_refundable']": {'true': 0.5, 'false': 0.5},
"booking_info['purchased_insurance']": {'true': 0.2, 'false': 0.8},
"booking_info['amount_paid']": {'random_int(100, 1500)': 1.0},
'stored_payment_method': {'Points': 0.3, 'Credit Card': 0.4, 'Debit Card': 0.3},
"personal_info['frequent_flyer_status']": {'Gold': 0.4, 'Platinum': 0.3, 'null': 0.3}, 
"personal_info['passport_number']": passport_numbers,
"personal_info['loyalty_points']":{'random_int(0, 50000)': 1.0},
"flight_search_results": flight_search_results,
"user_provided_info['origin_airport']": origin_options, 
"user_provided_info['destination_airport']": destination_options, 
"user_provided_info['departure_date']": {"random_date('2025-06-01', '2025-07-15')": 1.0}, 
"user_provided_info['flight_type']": {'One Way': 1.0},
"user_provided_info['preferred_flight_number']": {'BA9100': 1.0},
"user_provided_info['mobile_phone_number']": {
                    'same_as': "contact_info['mobile_phone_number']",  
                    'probability': 1
                        },
"user_provided_info['authenticator_code']": {
                    'same_as': "authenticator_api['authenticator_code']",  
                    'probability': 1
                        }
}



                