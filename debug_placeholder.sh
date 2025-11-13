#!/bin/bash

# Copy the function exactly
is_placeholder() {
    local value="$1"
    local var_name="$2"
    
    # Check for common placeholder patterns (exclude test values)
    if [[ "$value" == *"your-"* ]] || \
       [[ "$value" == *"generate-"* ]] || \
       [[ "$value" == *"GENERATE"* ]] || \
       [[ "$value" == *"placeholder"* ]] || \
       [[ "$value" == *"example"* ]] || \
       [[ "$value" == *"change-me"* ]] || \
       [[ "$value" == *"xxx"* ]] || \
       [[ "$value" == *"dev-"*"-placeholder" ]]; then
        return 0  # Is placeholder
    fi
    
    # Check for empty values that shouldn't be empty
    if [[ -z "$value" ]] && ( [[ "$var_name" == *"_KEY"* ]] || [[ "$var_name" == *"_SECRET"* ]] || [[ "$var_name" == *"_PASSWORD"* ]] ); then
        return 0  # Is placeholder (empty sensitive value)
    fi
    
    return 1  # Not placeholder
}

# Test it
value="test-client-secret"
var_name="GOOGLE_CLIENT_SECRET"

echo "Testing value: '$value'"
echo "Testing var_name: '$var_name'"

if is_placeholder "$value" "$var_name"; then
    echo "Result: PLACEHOLDER"
else
    echo "Result: NOT PLACEHOLDER"
fi
