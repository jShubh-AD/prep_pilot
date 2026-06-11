import re

def sanitize_filename(text: str) -> str:
    # replace any character not in [a-zA-Z0-9._-] with underscore
    return re.sub(r'[^a-zA-Z0-9._-]', '_', text)