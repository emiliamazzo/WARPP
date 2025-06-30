react_example = """  
# NOTE: In the following example, Observations are placeholders for values coming from the user or tool call outputs.

Thought 1: A new customer wants to withdraw from retirement. Before touching any funds, I must authenticate. Greet customer and ask for phone number.  
Action 1: Respond: I can help with your retirement withdrawal. First, I need to verify your identity. Could you please provide your phone number?

Thought 2: Send the customer a code.  
Action 2: Call send_verification_text(USER_PROVIDED_PHONE_NUMBER)  
You need to invoke a tool so emit exactly a JSON object that follows OpenAI’s function-calling format for send_verification_text(USER_PROVIDED_PHONE_NUMBER)  

Thought 3: I need to collect the code from the customer.
Action 3: Respond: "A verification message has been sent to your phone number 5551237890. Please provide the verification code you received." 

Thought 4: I need to confirm their identity using our verification tool.
Action 4: Call code_verifier(code=USER_PROVIDED_PHONE_NUMBER, customer_id=CUSTOMER_ID)
You need to invoke a tool so emit exactly a JSON object that follows OpenAI’s function-calling format for code_verifier(code=USER_PROVIDED_PHONE_NUMBER, customer_id=CUSTOMER_ID)

Thought 5: Authentication was successful. I must now inform the customer and ask them if they are ready to proceed with their request.  
Action 5: Respond: You have been successfully authenticated. Are you ready to proceed with your request?  

Thought 6: Back to the customer's request. They want to withdraw retirement funds. I should first check if they are eligible.  
Action 6: Call check_withdrawal_eligibility_extra(customer_id=CUSTOMER_ID)  
You need to invoke a tool so emit exactly a JSON object that follows OpenAI’s function-calling format for check_withdrawal_eligibility_extra(customer_id=CUSTOMER_ID)  

Thought 7: Since they can withdraw funds, I will now ask how much they would like to withdraw.  
Action 7: Respond: You're eligible to make a withdrawal. How much would you like to withdraw from your retirement account?  

Thought 8: The customer would like to withdraw $2,000. I will now process the withdrawal.  
Action 8: Call process_retirement_withdrawal(customer_id=CUSTOMER_ID, withdrawal_amount=USER_PROVIDED_AMOUNT)  
You need to invoke a tool so emit exactly a JSON object that follows OpenAI’s function-calling format for process_retirement_withdrawal(customer_id=CUSTOMER_ID, withdrawal_amount=USER_PROVIDED_AMOUNT)  

Thought 9: The withdrawal was successful. I should now close the case.  
Action 9: Call complete_case(customer_id=5772654)  
You need to invoke a tool so emit exactly a JSON object that follows OpenAI’s function-calling format for complete_case(customer_id=CUSTOMER_ID)  

Thought 10: The case is now complete. I should inform the customer and thank them.  
Action 10: Respond: Your $2,000 withdrawal has been successfully processed and your case is now closed.
"""

