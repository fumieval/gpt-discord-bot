from enum import Enum
from dataclasses import dataclass
import openai
from typing import Optional, List
from src.constants import (
    BOT_INSTRUCTIONS,
    BOT_NAME,
    EXAMPLE_CONVOS,
)
import discord
from src.base import Message, Conversation
from src.utils import split_into_shorter_messages, close_thread, logger
import src.store
import json

MY_BOT_NAME = BOT_NAME
MY_BOT_EXAMPLE_CONVOS = EXAMPLE_CONVOS


class CompletionResult(Enum):
    OK = 0
    TOO_LONG = 1
    INVALID_REQUEST = 2
    OTHER_ERROR = 3
    MODERATION_FLAGGED = 4
    MODERATION_BLOCKED = 5


@dataclass
class CompletionData:
    status: CompletionResult
    reply_text: Optional[str]
    status_text: Optional[str]


async def generate_completion_response(
    messages: List[Message], user: str, database, query_ids
) -> CompletionData:
    try:
        convo = Conversation(instruction=BOT_INSTRUCTIONS,
            messages=messages,
            knowledge_summary=src.store.gen_knowledge_summary(database),
            queried_knowledge=src.store.restore_knowledge(database, query_ids)
            )
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=1.0,
            top_p=0.9,
            max_tokens=512,
            stop=["<|endoftext|>"],
            messages=convo.renderChat(),
        )
        raw_response = response.choices[0].message.content
        try:
            begin = raw_response.find('{')
            end = raw_response.rfind('}') + 1
            print(raw_response[begin:end])
            obj = json.loads(raw_response[begin:end])
            if len(query_ids) == 0 and len(obj['query']) > 0 and not ('confident' in obj and obj['confident']):
                result = await generate_completion_response(messages, user, database, query_ids=obj['query'])
                return result
            else:
                reply_text=obj['reply']
                if "text" in reply_text:
                    reply_text=reply['text']
                if 'learn' in obj and obj['learn'] and not obj['is_question']:
                    src.store.insert_knowledge(database, obj['title'], messages[-1].render())
                if 'forget' in obj:
                    src.store.delete_knowledge(database, obj['forget'])
                return CompletionData(
                    status=CompletionResult.OK, reply_text=reply_text, status_text=None
                )
        except Exception as e:
            logger.exception(raw_response, e)
            return CompletionData(
                status=CompletionResult.OK, reply_text=raw_response, status_text=None
            )
    except openai.error.InvalidRequestError as e:
        if "This model's maximum context length" in e.user_message:
            return CompletionData(
                status=CompletionResult.TOO_LONG, reply_text=None, status_text=str(e)
            )
        else:
            logger.exception(e)
            return CompletionData(
                status=CompletionResult.INVALID_REQUEST,
                reply_text=None,
                status_text=str(e),
            )
    except Exception as e:
        logger.exception(e)
        return CompletionData(
            status=CompletionResult.OTHER_ERROR, reply_text=None, status_text=str(e)
        )


async def process_response(
    user: str, thread: discord.Thread, response_data: CompletionData
):
    status = response_data.status
    reply_text = response_data.reply_text
    status_text = response_data.status_text
    if status is CompletionResult.OK:
        sent_message = None
        if not reply_text:
            sent_message = await thread.send(
                embed=discord.Embed(
                    description=f"**Invalid response** - empty response",
                    color=discord.Color.yellow(),
                )
            )
        else:
            shorter_response = split_into_shorter_messages(reply_text)
            for r in shorter_response:
                sent_message = await thread.send(r)

    elif status is CompletionResult.TOO_LONG:
        await close_thread(thread)
    elif status is CompletionResult.INVALID_REQUEST:
        await thread.send(
            embed=discord.Embed(
                description=f"**Invalid request** - {status_text}",
                color=discord.Color.yellow(),
            )
        )
    else:
        await thread.send(
            embed=discord.Embed(
                description=f"**Error** - {status_text}",
                color=discord.Color.yellow(),
            )
        )
