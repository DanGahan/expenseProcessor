#!/bin/bash

# Calculate the date for the coming Monday
today=$(date +%u)  # Day of week (1=Monday, 7=Sunday)

if [ "$today" -eq 1 ]; then
    # If today is Monday, use next Monday
    days_until_monday=7
else
    # Calculate days until next Monday
    days_until_monday=$((8 - today))
fi

# Get the date for coming Monday in DDMMYY format
monday_date=$(date -v +${days_until_monday}d +%d%m%y)

# Create directory name
dir_name="wc ${monday_date}"

# Create the directory
mkdir -p "$dir_name"

# Source file
source_file="Atos Travel Pre-Approval Form v2.3_Dan_Gahan_wc_DD_MM_YY.xlsx"

# Check if source file exists
if [ ! -f "$source_file" ]; then
    echo "Error: Source file '$source_file' not found"
    exit 1
fi

# Format the date for the filename (DD_MM_YY)
day=$(date -v +${days_until_monday}d +%d)
month=$(date -v +${days_until_monday}d +%m)
year=$(date -v +${days_until_monday}d +%y)
filename_date="${day}_${month}_${year}"

# Destination file
dest_file="$dir_name/Atos Travel Pre-Approval Form v2.3_Dan_Gahan_wc_${filename_date}.xlsx"

# Copy and rename the file
cp "$source_file" "$dest_file"

echo "Created directory: $dir_name"
echo "Copied file to: $dest_file"
