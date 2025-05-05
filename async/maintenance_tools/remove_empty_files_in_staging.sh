#!/bin/bash

# Specify the folder path
folder_path="/volume-mnt-point/staging"

# Change to the specified folder
cd "$folder_path" || exit

# Find and remove empty files
empty_files=$(find . -type f -empty)

# Loop through empty files and remove them
for file in $empty_files; do
    echo "Removing file: $file"
    rm "$file"
done

echo "Empty files have been removed."

