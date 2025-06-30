first_utterance_generator_prompt = """You are a customer service expert helping design a chatbot for the {DOMAIN} domain.
Your task is to generate natural customer utterances for two different service intents.
For each intent, write 50 different ways (variations allowed) that a customer might express the intent when interacting with a chatbot.
Include formal, informal, polite, vague, annoyed, typo-ridden, short, long, and slangy versions. Prioritize variety and realism.
Do not number the utterances.
Group them under clearly labeled sections: Intent: [INTENT]
Do not include explanations, just the utterances.
Each utterance should be on its own line.
**Intents:
Intent 1: {INTENT1}
Intent 2: {INTENT2}
**Output:
A list of 50 utterances per intent, separated into two labeled sections."""