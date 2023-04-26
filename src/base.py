from dataclasses import dataclass
from typing import Optional, List
import itertools
import re

SEPARATOR_TOKEN = "<|endoftext|>"

def gen_prompt(message, table, quotes):
    return f'''
{message}

Reply to the previous message as a single JSON object:

{{
    "is_question": boolean // where the message above is a question
    "learn": boolean // true if you gained knowledge that's not in the table below, or if the user wants you to know
    "title": string // terse summary of the knowledge you gained, in subject-verb-object form
    "query": [number] // list of IDs of the knowledge you should consult
    "confident": boolean // true if you are confident about your reply
    "forget": [number] // list of IDs of the knowledge that turned out to be incorrect
    "reply": string
}}

Use the following table of knowledge. Only you can see this table.

{table}

JSON形式を守ってください。

Also, please take the following quotes into consideration.

{quotes}

Occasionally say "ワイトもそう思います。" if you heartily agree with the previous non-question message.
'''

@dataclass(frozen=True)
class Message:
    user: str
    text: Optional[str] = None

    def render(self):
        result = self.user + ": "
        if self.text is not None:
            result += " " + re.sub("<@[0-9]+>", "", self.text).strip()
        return result

@dataclass
class Conversation:
    instruction: str
    queried_knowledge: str
    knowledge_summary: str
    messages: List[Message]

    def prepend(self, message: Message):
        self.messages.insert(0, message)
        return self

    def renderChat(self):
        f = lambda msg: {"role": "assistant" if msg.user == "Wight" else "user", "content": msg.render()}
        header = {"role": "user", "content": self.instruction}
        footer = {"role": "user", "content": gen_prompt(message=self.messages[-1].render(), table=self.knowledge_summary, quotes=self.queried_knowledge)}
        result = [header] + list(map(f, self.messages[:-1])) + [footer]
        print(result)
        return result

@dataclass(frozen=True)
class Config:
    name: str
    instructions: str
    example_conversations: List[Conversation]
