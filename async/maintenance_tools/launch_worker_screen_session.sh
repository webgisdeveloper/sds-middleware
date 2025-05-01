#!/bin/bash

# Define the base name for the screen sessions
SESSION_BASE_NAME="worker-"

# Path to your Python script
SCRIPT_PATH="<path/to/worker.py>"

# Number of screen sessions to create
NUM_SESSIONS=4

# Get the directory path of the script
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")

# Loop to create and launch the screen sessions
for ((i=1; i<=NUM_SESSIONS; i++)); do
  # Construct the screen session name
  SESSION_NAME="${SESSION_BASE_NAME}${i}"
  
  # Create a new detached screen session with the specified name
  screen -dmS "$SESSION_NAME" 

  # Change directory and execute your Python script in the screen session
  screen -S "$SESSION_NAME" -X stuff "cd "$SCRIPT_DIR"; python $(basename "$SCRIPT_PATH")\n"
  
  echo "Launched screen session: $SESSION_NAME"
done

