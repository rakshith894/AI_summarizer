"""
Prompt construction for the AI Summarizer.
Keeping this in its own module makes it easy to tune wording,
add new styles, or A/B test prompts without touching main.py.
"""

LENGTH_INSTRUCTIONS = {
    "short": "in 2-3 concise sentences",
    "medium": "in a single well-organized paragraph (5-7 sentences)",
    "detailed": "in a detailed multi-paragraph summary covering all key points",
}

STYLE_INSTRUCTIONS = {
    "paragraph": "Write it as flowing prose.",
    "bullets": "Write it as a bulleted list of the key points.",
    "one-liner": "Write it as a single, punchy sentence.",
}


def build_prompt(text: str, length: str = "short", style: str = "paragraph") -> str:
    """
    Build the summarization prompt sent to the LLM.

    Args:
        text: The raw text to summarize.
        length: One of "short", "medium", "detailed".
        style: One of "paragraph", "bullets", "one-liner".

    Returns:
        A fully formed prompt string.
    """
    length_instruction = LENGTH_INSTRUCTIONS.get(length, LENGTH_INSTRUCTIONS["short"])
    style_instruction = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["paragraph"])

    return (
        "You are a precise summarization assistant. Summarize the text below "
        f"{length_instruction}. {style_instruction} "
        "Do not add opinions or information that isn't in the original text.\n\n"
        "TEXT TO SUMMARIZE:\n"
        "-----\n"
        f"{text}\n"
        "-----\n\n"
        "SUMMARY:"
    )