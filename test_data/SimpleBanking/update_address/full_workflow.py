update_address_workflow = """
1. Retrieve Account Information
   - Call get_account_type_extra(customer_id)
   - Inform the customer of their account type
   - Ask for confirmation to proceed with the address update

2. Collect and Validate New Address
   - Ask the customer for new address details (street, city, state, zip, country)
   - Call validate_address(street, city, state, zip_code, country)
   - If validation fails:
     - Inform the customer and ask to re-enter address
     - Retry validation once

3. Update Address
   - Call update_address(customer_id, street, city, state, zip_code, country)
   - Confirm the update with the customer

4. Apply Address Hold
   a. If client_level is "STANDARD":
      - Call apply_address_hold(customer_id)
      - Inform customer of hold duration and affected transactions

5. Complete the Case
   - Call complete_case(customer_id)
   - Provide confirmation number and close the case

6. Error Handling
   - If any step fails:
     - Retry once
     - If still failing, inform the customer and escalate if needed
     - Call complete_case(customer_id)
"""
