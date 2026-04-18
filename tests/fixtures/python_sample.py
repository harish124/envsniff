"""Sample Python file with all os.environ patterns for testing envsniff."""

import os

# Pattern 1: os.getenv with default
db_host = os.getenv("DATABASE_HOST", "localhost")

# Pattern 2: os.getenv without default (required)
api_key = os.getenv("API_KEY")

# Pattern 3: os.environ.get with default
port = os.environ.get("PORT", "8080")

# Pattern 4: os.environ.get without default
secret = os.environ.get("SECRET_TOKEN")

# Pattern 5: os.environ subscript (required, raises KeyError if missing)
database_url = os.environ["DATABASE_URL"]

# Pattern 6: nested / multi-line usage
def get_config():
    return {
        "debug": os.getenv("DEBUG", "false"),
        "redis_url": os.environ["REDIS_URL"],
    }

# Pattern 7: inline with default expression
timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))

# Edge case: dynamic key (should not be extracted as named var)
dynamic_key = "MY_VAR"
dynamic_val = os.getenv(dynamic_key)  # cannot statically resolve

# Edge case: multiline call
log_level = os.environ.get(
    "LOG_LEVEL",
    "INFO",
)
