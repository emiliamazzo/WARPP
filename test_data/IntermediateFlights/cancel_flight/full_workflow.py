cancel_flight_workflow = """
1. Retrieve Customer Loyalty Information
   a. Call `get_customer_loyalty_info_extra(customer_id)`
      - If the customer has more than 30,000 loyalty points: welcome them as a preferred client
      - If less: thank them as a new customer

2. Retrieve Booking Information
   a. Call `get_booking_details_extra(customer_id)` to get the original booking rules.
   b. If this booking’s policy does not allow cancellations at all:
        -Say: “I’m sorry, your fare rule at purchase did not permit cancellation.”
        -Skip directly to step 8 and close.
   c. If the policy does allow cancellation, acknowledge:
        -“Your fare permits cancellations—let’s now confirm whether operations still allow it.”
        -Then always continue to step 3.

3. Check Live Cancellation Blockers
   a. Call `check_cancellation_blockers(booking_id)` to see if there are any blockers that prevent the cancellation.
   b. If response is:
      - "eligible": proceed
      - "api_failure": apologize to the client for the technical difficulties, prompt them to call again at a later time, and proceed directly to step 8.
      - any other response: inform the customer that there is a blocker that prevents them from cancelling the flight at this time. Offer and explanation, apologize, and proceed directly to step 8.

4. Calculate Cancellation Fee
   a. Call `calculate_cancellation_fee(customer_id, booking_id)`

5. Process Flight Cancellation
   a. Describe policy + fee to the customer
   b. If customer confirms, call `cancel_flight(booking_id)`

6. Process Refund or Issue Travel Credit
   a. If refundable or insurance was purchased for this booking:
      - Call `process_refund(customer_id, booking_id, payment_method, cancellation_fee)` using the payment_method stored for the customer. 
   b. Otherwise:
      - Call `issue_travel_credit(customer_id, booking_id, cancellation_fee)`

7. Confirm Cancellation and Provide Next Steps
   a. Share final status, refund/credit amount, and confirmation number.

8. Complete Case
   a. Call `complete_case(customer_id)`
   b. Thank the customer.

Error Handling
a. On any persistent failure:
  - Retry once
  - Inform the customer
  - Call complete_case to close out
"""
