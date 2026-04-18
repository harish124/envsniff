#!/bin/bash
# Sample shell script with env var patterns for testing envsniff

# Pattern 1: ${VAR} syntax
echo "Starting with host ${DATABASE_HOST}"

# Pattern 2: $VAR syntax (simple variable reference)
echo "API key: $API_KEY"

# Pattern 3: with default via parameter expansion
PORT=${PORT:-8080}

# Pattern 4: required variable (fail if unset)
: "${SECRET_TOKEN:?SECRET_TOKEN must be set}"

# Pattern 5: in command argument
curl -H "Authorization: Bearer ${AUTH_TOKEN}" https://api.example.com

# Pattern 6: export
export DEBUG="${DEBUG:-false}"

# Pattern 7: assignment from env
LOG_LEVEL=$LOG_LEVEL

# Edge cases: shell special variables (should be SKIPPED)
echo "Process: $$"       # $$ = PID
echo "Exit: $?"          # $? = last exit code
echo "Background: $!"    # $! = last background PID
echo "Script: $0"        # $0 = script name
echo "Arg1: $1"          # positional parameter
echo "All args: $@"      # all args
echo "All args: $*"      # all args
echo "Count: $#"         # arg count

# Pattern 8: lowercase vars (should be SKIPPED per regex requiring uppercase)
echo "home is $HOME"     # uppercase - should be found
echo "path: $PATH"       # uppercase - should be found
