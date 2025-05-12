from anthropic import AsyncAnthropic
from dotenv import load_dotenv
import os

load_dotenv()


class ClaudeLLM:
    def __init__(self, model="claude-3-5-sonnet-20241022"):
        self.client = AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        self.model = model

    async def chat(self, messages):
        # Extract system prompt and actual messages
        system_prompt = ""
        cleaned_messages = []

        for m in messages:
            if m["role"] == "system":
                system_prompt = m["content"]
            else:
                cleaned_messages.append(m)

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=0.5,
            system=system_prompt,
            messages=cleaned_messages,
        )
        return response.content[0].text.strip()
