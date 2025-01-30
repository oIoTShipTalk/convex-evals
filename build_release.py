#!/usr/bin/env python3

import os
from runner.models.anthropic_codegen import build_release_guidelines as build_anthropic_guidelines
from runner.models.openai_codegen import build_release_guidelines as build_openai_guidelines

def main():    
    os.makedirs("dist", exist_ok=True)
    
    # Generate rules (we could do more model-specific ones in the future)
    # Using a very specific filename here to make it clear for AI usage what this is

    with open("dist/anthropic_convex_rules.txt", "w") as f:
        f.write(build_anthropic_guidelines())
    
    with open("dist/openai_convex_rules.txt", "w") as f:
        f.write(build_openai_guidelines())

if __name__ == "__main__":
    main() 