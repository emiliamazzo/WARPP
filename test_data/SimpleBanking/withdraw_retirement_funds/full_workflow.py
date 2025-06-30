withdraw_retirement_funds_workflow = '''
1. Check Withdrawal Eligibility
   - Call `check_withdrawal_eligibility_extra(customer_id)`
   - If not eligible:
     - Inform the customer and close the case by calling `complete_case(customer_id)`.

2. Collect Withdrawal Amount
   - Ask the customer how much they would like to withdraw

3. Process Withdrawal
   - Call `process_retirement_withdrawal(customer_id, withdrawal_amount)`
   - Confirm success and share final amount with customer

4. Complete Case
   - Call `complete_case(customer_id)`
   - Provide a confirmation message to the customer

5. Error Handling
   - If any step fails:
     - Retry once
     - If still failing, inform the customer and close the case
'''
