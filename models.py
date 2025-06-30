from pydantic import BaseModel
from typing import Optional, Any, Dict, Union, List

class AuthenticatedCustomerContext(BaseModel):
    """
    Represents the context of a customer.

    This class holds customer-specific data such as the customer's ID, the domain of interaction,
    identified intents, routines associated with these intents, and a collection of available tools.
    It also includes a dictionary to store client information gathered from various tools.

    Attributes:
        customer_id (Union[int, str], optional): The unique identifier for the customer. It can be an integer or a string.
        domain (str, optional): The domain of interaction for the customer (ex. Banking, Hospital, Flights).
        intent_identified (str, optional): The identifier for the recognized intent of the customer.
        intent_full_routine (str, optional): The full routine related to the identified intent.
        intent_personalized_routine (str, optional): The personalized routine for the identified intent.
        intent_all_tools (List, optional): A list of tools associated with all possible intents.
        available_tools (Any, optional): The available tools for the customer, defaults to an empty list.
        client_info (dict, optional): A dictionary storing the results from info-gathering tools. Defaults to an empty dictionary.
    """
    customer_id: Optional[Union[int, str]] = None
    domain: Optional[str] = None
    intent_identified: Optional[str] = None
    intent_full_routine: Optional[str] = None
    intent_personalized_routine: Optional[str] = None
    intent_all_tools: Optional[List] = None
    available_tools: Optional[Any] = []
    client_info: Dict[str, Any] = {} 
    model: str = "gpt-4o"
    api_key: str = None


    class Config:
        """Configuration for Pydantic model to allow mutation."""
        allow_mutation = True


    def update_client_info(self, new_info: Dict[str, Any]) -> None:
        """
        Updates the client information with new data gathered from tools.

        Args:
            new_info (Dict[str, Any]): The new client information to update.

        Returns:
            None: This method does not return any value. It updates the client_info dictionary.
        
        If `new_info` is non-empty, it will be merged with the existing `client_info`.
        """
        if new_info:
            self.client_info.update(new_info)

            
    def __str__(self) -> str:
        """
        Returns a string representation of the customer context.

        This representation excludes function objects and focuses on serializable fields such as customer ID,
        domain, identified intent, and client information. If available, it also provides a summary of the 
        full or personalized routine.

        Returns:
            str: A string summary of the customer's context, including identifiable information and routines.
        """        # create dic of serializable fields
        serializable_dict = {
            "customer_id": self.customer_id,
            "domain": self.domain,
            "intent_identified": self.intent_identified,
            "client_info": self.client_info
        }
        
        # the routine as a string summary
        if self.intent_full_routine:
            serializable_dict["intent_full_routine"] = f"<routine for {self.intent_identified}>"
        if self.intent_personalized_routine:
            serializable_dict["intent_personalized_routine"] = f"<personalized routine for {self.intent_identified}>"
            
        return str(serializable_dict)