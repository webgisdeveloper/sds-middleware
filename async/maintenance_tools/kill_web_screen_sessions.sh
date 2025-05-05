#!/bin/bash

# Define the base name for the screen sessions
SESSION_BASE_NAME="web"

# Get a list of running screen sessions
SCREEN_SESSIONS=$(screen -ls | awk '{print $1}')

# Loop through the screen sessions
for SESSION in $SCREEN_SESSIONS; do
  # Extract the session name from the session ID
  SESSION_NAME=$(echo "$SESSION" | awk -F '.' '{print $2}')

  # Check if the session name matches the naming convention
  if [[ $SESSION_NAME == ${SESSION_BASE_NAME} ]]; then
    # Kill the screen session
    screen -S "$SESSION_NAME" -X quit
    echo "Killed screen session: $SESSION_NAME"
  fi
done

