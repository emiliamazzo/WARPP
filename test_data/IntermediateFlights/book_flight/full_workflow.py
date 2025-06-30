book_flight_workflow = '''
## Step 1: Ask for Basic Flight Details (Always)
- Ask the customer for:
  - **Origin**
  - **Destination**
  - **Departure date**

## Step 2: Check Customer Priority Status
- Call `get_customer_frequent_flyer_status_extra(customer_id)` to check if the customer is a frequent flyer.
  - **If frequent flyer status is None**:
    - Go to Step 3.
  - **If frequent flyer status is not None**:
    - Skip to Step 4.

## Step 3: Search Regular Flights
- Call `search_regular_flights(customer_id, origin_airport, destination_airport, departure_date)`.
- You must always share with the client the information from the search. Always include the flight number. Ask the client for thier preferred flight and get their confirmation before proceeding step 5.

## Step 4: Search Priority Flights
- Call `search_priority_flights(customer_id, origin_airport, destination_airport, departure_date)`.
- You must always share with the client the information from the search. Always include the flight number. Ask the client for thier preferred flight and get their confirmation before proceeding step 5.

## Step 5: Check Passport Information
- Call `get_passport_info_extra(customer_id)`.
- If no passport number is stored in the system, ask the user for it. 

## Step 6: Check Visa Information
- Frequent flyer visa information is already on the system. For non-frequent flyer customers (frequent flyer status is None):
  - Call `check_visa_requirements(origin_airport, destination_airport)`.
  - Inform customer if visa is required.

## Step 7: Retrieve Payment Method and Create Booking
- Call `get_customer_payment_method_extra(customer_id)`.
- If method is Points: go to step 8
- If method is not Points: skip to step 9

## Step 8: Create Booking with Points
  - Call `create_booking_with_points(flight_number)` 
  
## Step 9: Create Booking with Payment Method
  - Call `create_booking(flight_number)`.

## Step 10: Final Confirmation and Communication
- Provide full booking details and confirmation number.
- Call `complete_case(customer_id)`.
- Thank the customer: "Thank you for booking with us. Have a pleasant journey!"

## Error Handling and Resolution
- At any point if a critical failure (e.g.,tool fails multiple times):
  - Call `complete_case(customer_id)` to close the case after informing the customer.
'''
