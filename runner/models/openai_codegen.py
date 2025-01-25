import openai
import os
from . import ConvexCodegenModel, SYSTEM_PROMPT
import re
from markdown_it import MarkdownIt
from markdown_it.token import Token
from typing import Union
from .guidelines import Guideline, GuidelineSection, CONVEX_GUIDELINES
from braintrust import wrap_openai

class OpenAIModel(ConvexCodegenModel):
    def __init__(self, model: str):
        assert model in ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini"]
        self.chain_of_thought = "o1" not in model
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")

        self.client = wrap_openai(openai.OpenAI(
            base_url="https://api.braintrust.dev/v1/proxy",
            api_key=api_key,
        ))
        self.model = model

    def generate(self, prompt: str):
        if self.chain_of_thought:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt(prompt, self.chain_of_thought)},
                ],
                max_tokens=16384,
                seed=1,
            )
            return self._parse_response(response.choices[0].message.content)
        else:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt(prompt, self.chain_of_thought)},
                ],
                max_completion_tokens=16384,
                seed=1,
            )
            return self._parse_response(response.choices[0].message.content)

    def _parse_response(self, response: str):
        md = MarkdownIt()
        tokens = md.parse(response)

        files = {}
        current_file = None
        in_files_section = False
        code_lang = None

        for i, token in enumerate(tokens):
            if token.type == "heading_open" and token.tag == "h1":
                title_token = tokens[i + 1]
                if title_token.content == "Files":
                    in_files_section = True
                    continue

            if not in_files_section:
                continue

            if token.type == "heading_open" and token.tag == "h2":
                title_token = tokens[i + 1]
                current_file = title_token.content.strip()
            elif token.type == "fence" and current_file:
                code_lang = token.info
                files[current_file] = token.content.strip()
                current_file = None

        return files


TASK_INSTRUCTION = """
Your task is to generate a Convex backend based on the following task description:
```
%s
```
"""


def render_guidelines(node: Union[GuidelineSection, Guideline], header="#"):
    if isinstance(node, Guideline):
        yield "- "
        yield node.content
        yield "\n"
    else:
        words = node.name.split("_")
        words[0] = words[0].capitalize()
        yield f"{header} {' '.join(words)}\n"
        for child in node.children:
            yield from render_guidelines(child, header + "#")
        yield "\n"


OPENAI_CONVEX_GUIDELINES = "".join(render_guidelines(CONVEX_GUIDELINES))


def chain_of_thought_prompt(prompt: str):
    yield TASK_INSTRUCTION % prompt
    yield """
Before writing any code, analyze the task and think through your approach. Start with an h1 Analysis
section to show your thought process, covering the following areas:
1. Summarize the task requirements
2. List out the main components needed for the backend
3. Design the public API:
   - List each function with its purpose and expected arguments
4. Plan the schema design (if needed):
   - List each table with its fields and types
5. Outline background processing requirements (if any):

After your analysis, output all files within an h1 Files section that has an h2 section for
each necessary file for a Convex backend that implements the requested functionality.
For example, correct output looks like

# Analysis
...
# Files
## package.json
```
...
```
## convex/schema.ts
```
...
```
"""
    yield OPENAI_CONVEX_GUIDELINES
    yield "Begin your response with your thought process, then proceed to generate the necessary files for the Convex backend."


def reasoning_prompt(prompt: str):
    yield TASK_INSTRUCTION % prompt
    yield """
Output all files within an h1 Files section that has an h2 section for
each necessary file for a Convex backend that implements the requested functionality.
For example, correct output looks like

# Files
## package.json
```
...
```
## convex/schema.ts
```
...
```
"""
    yield OPENAI_CONVEX_GUIDELINES


def user_prompt(prompt: str, chain_of_thought: bool = True):
    if chain_of_thought:
        return "\n".join(chain_of_thought_prompt(prompt))
    else:
        return "\n".join(reasoning_prompt(prompt))
