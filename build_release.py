#!/usr/bin/env python3

import os
from runner.models.anthropic_codegen import build_release_guidelines as build_anthropic_guidelines
from runner.models.openai_codegen import build_release_guidelines as build_openai_guidelines

def main():
    # Create dist directory if it doesn't exist
    os.makedirs("dist", exist_ok=True)
    
    # Generate Anthropic guidelines
    with open("dist/anthropic_claude_sonnet_3_5.txt", "w") as f:
        f.write(build_anthropic_guidelines())
    
    # Generate OpenAI guidelines
    with open("dist/openai_gpt_4o.txt", "w") as f:
        f.write(build_openai_guidelines())

if __name__ == "__main__":
    main() 