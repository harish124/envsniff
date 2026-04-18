"""Regex-based heuristic describer — no API calls required.

Covers ~80% of common environment variable naming conventions and
returns a ``(description, example_value)`` pair for any variable name.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Exact-match overrides (checked before pattern rules)
# ---------------------------------------------------------------------------
_EXACT: dict[str, tuple[str, str]] = {
    "DATABASE_URL": ("PostgreSQL/MySQL connection string", "postgres://user:pass@localhost/dbname"),
    "DB_URL": ("Database connection string", "postgres://user:pass@localhost/dbname"),
    "REDIS_URL": ("Redis connection string", "redis://localhost:6379/0"),
    "MONGO_URI": ("MongoDB connection URI", "mongodb://localhost:27017/mydb"),
    "API_KEY": ("API authentication key", "your-api-key-here"),
    "API_SECRET": ("API secret for HMAC signing", "your-api-secret-here"),
    "AUTH_TOKEN": ("Authentication bearer token", "your-auth-token-here"),
    "JWT_SECRET": ("Secret key for signing JWT tokens", "a-very-long-random-secret"),
    "SECRET_KEY": ("Application secret key for cryptographic operations", "a-very-long-random-secret"),
    "DEBUG": ("Enable debug mode (true/false)", "false"),
    "VERBOSE": ("Enable verbose logging output (true/false)", "false"),
    "PORT": ("Port number the server listens on", "8080"),
    "HOST": ("Hostname or IP address the server binds to", "0.0.0.0"),
    "DATABASE_PASSWORD": ("Database user password", "your-db-password"),
    "DATABASE_HOST": ("Database server hostname", "localhost"),
    "DATABASE_PORT": ("Database server port number", "5432"),
    "DATABASE_NAME": ("Name of the database to connect to", "mydb"),
    "DATABASE_USER": ("Database user name", "dbuser"),
}

# ---------------------------------------------------------------------------
# Suffix/prefix pattern rules
# ---------------------------------------------------------------------------
# Each rule: (suffix, description_template, example_template)
# {service} is replaced with the extracted service name prefix.
_SUFFIX_RULES: list[tuple[str, str, str]] = [
    ("_URL",      "{service} service URL",                   "https://{service_lower}.example.com"),
    ("_URI",      "{service} URI",                           "https://{service_lower}.example.com"),
    ("_KEY",      "{service} API key",                       "your-{service_lower}-key-here"),
    ("_TOKEN",    "{service} authentication token",          "your-{service_lower}-token-here"),
    ("_SECRET",   "{service} secret value",                  "your-{service_lower}-secret-here"),
    ("_PASSWORD", "{service} password",                      "your-{service_lower}-password"),
    ("_PASSWD",   "{service} password",                      "your-{service_lower}-password"),
    ("_PASS",     "{service} password",                      "your-{service_lower}-password"),
    ("_HOST",     "Hostname for {service} service",          "{service_lower}.example.com"),
    ("_PORT",     "Port number for {service} service",       "8080"),
    ("_ENABLED",  "Enable {service} feature (true/false)",   "true"),
    ("_DISABLED", "Disable {service} feature (true/false)",  "false"),
    ("_FLAG",     "{service} feature flag (true/false)",     "false"),
    ("_ACTIVE",   "{service} active flag (true/false)",      "true"),
    ("_TIMEOUT",  "Timeout in seconds for {service}",        "30"),
    ("_RETRIES",  "Number of retries for {service}",         "3"),
    ("_MAX",      "Maximum value for {service}",             "100"),
    ("_MIN",      "Minimum value for {service}",             "0"),
    ("_SIZE",     "Size limit for {service}",                "1024"),
    ("_LIMIT",    "Rate or count limit for {service}",       "100"),
    ("_TTL",      "Time-to-live in seconds for {service}",   "3600"),
    ("_INTERVAL", "Interval in seconds for {service}",       "60"),
    ("_COUNT",    "Count of {service}",                      "10"),
    ("_NAME",     "Name of the {service}",                   "{service_lower}-name"),
    ("_PATH",     "Filesystem path for {service}",           "/var/{service_lower}"),
    ("_DIR",      "Directory path for {service}",            "/var/{service_lower}"),
    ("_FILE",     "File path for {service}",                  "/etc/{service_lower}.conf"),
    ("_REGION",   "Cloud region for {service}",              "us-east-1"),
    ("_BUCKET",   "Cloud storage bucket for {service}",      "{service_lower}-bucket"),
    ("_QUEUE",    "Message queue name for {service}",        "{service_lower}-queue"),
    ("_TOPIC",    "Message topic for {service}",             "{service_lower}-topic"),
    ("_ENDPOINT", "API endpoint URL for {service}",          "https://api.{service_lower}.com"),
    ("_DSN",      "Data source name for {service}",          "postgres://localhost/{service_lower}"),
    ("_CERT",     "TLS certificate path for {service}",      "/etc/ssl/{service_lower}.crt"),
    ("_PRIVATE",  "Private key for {service}",               "-----BEGIN PRIVATE KEY-----"),
]

# Exact-name rules for bare names (no suffix)
_BARE_RULES: dict[str, tuple[str, str]] = {
    "PORT":    ("Port number the server listens on", "8080"),
    "HOST":    ("Hostname or IP address the server binds to", "0.0.0.0"),
    "DEBUG":   ("Enable debug mode (true/false)", "false"),
    "VERBOSE": ("Enable verbose logging output (true/false)", "false"),
    "ENV":     ("Deployment environment name", "production"),
    "ENVIRONMENT": ("Deployment environment name", "production"),
}


def _extract_service(name: str, suffix: str) -> str:
    """Extract the service prefix from *name* by removing *suffix*."""
    upper = name.upper()
    service = upper[: -len(suffix)] if upper.endswith(suffix) else upper
    # Convert SNAKE_CASE → Title Case for readability
    return service.replace("_", " ").title()


def describe_var(name: str) -> tuple[str, str]:
    """Return a ``(description, example_value)`` pair for *name*.

    Uses exact-match overrides, then suffix-pattern rules, then a generic
    fallback.  Never raises.

    Args:
        name: Environment variable name (any case).

    Returns:
        ``(description, example_value)`` — both are plain strings.
    """
    if not name:
        return ("Environment variable", "")

    upper = name.upper()

    # 1. Exact match
    if upper in _EXACT:
        return _EXACT[upper]

    # 2. Bare-name rules
    if upper in _BARE_RULES:
        return _BARE_RULES[upper]

    # 3. Suffix pattern rules
    for suffix, desc_template, example_template in _SUFFIX_RULES:
        if upper.endswith(suffix):
            service = _extract_service(name, suffix)
            service_lower = service.lower().replace(" ", "-")
            desc = desc_template.format(service=service, service_lower=service_lower)
            example = example_template.format(service=service, service_lower=service_lower)
            return (desc, example)

    # 4. Generic fallback
    readable = name.replace("_", " ").title()
    return (f"{readable} configuration value", "")
