import re

def sanitize_filename(filename: str) -> str:
    if not filename:
        return filename
    sanitized = filename.replace('[', '').replace(']', '')
    sanitized = sanitized.replace('/', '_').replace(' ', '_')
    sanitized = re.sub(r'[^A-Za-z0-9._-]', '_', sanitized)
    sanitized = re.sub(r'_+', '_', sanitized)
    return sanitized.strip('_')

__all__ = ["sanitize_filename"]
