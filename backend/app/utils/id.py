"""ID generation utilities."""

import uuid


def generate_id() -> str:
    """Generate a unique ID using UUID4."""
    return str(uuid.uuid4())