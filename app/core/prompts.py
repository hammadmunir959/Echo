def get_dispatch_summary_prompt(transcript: str) -> str:
    """
    return a prompt for the LLM to summarize a dispatch transcript.
    """
    return f"""### Instruction:
You are an expert emergency dispatch analyst. Analyze the following transcript and extract structured information.

### Transcript:
{transcript}

### Response:
"""
