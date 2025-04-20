#!/bin/bash

cd "$(dirname "$0")" || exit

# Function to handle interrupt signal
cleanup() {
    echo "Cleaning up..."
    kill 0
    exit 1
}

# Trap the interrupt signal (Ctrl+C)
trap cleanup SIGINT

# Initialize virtual to false
virtual=false

# Set agent_method to the first argument or default to 'multion'
agent_method="${1:-multion}"
# Set category based on --category flag or the second positional argument
category_name="${2:-}"

# Initialize timeout with default value
timeout=600

# Parse positional and optional arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --virtual) virtual=true; shift ;;
        --category) category_name="$2"; shift 2 ;;
        --timeout) timeout="$2"; shift 2 ;;
        *) 
            if [ -z "$agent_method" ]; then
                agent_method="$1"
                shift
            else
                shift
            fi
            ;;
    esac
done

prompts_directory="data/prompts"

categories=()
for category_dir in "$prompts_directory"/*; do
    category=$(basename "$category_dir")
    categories+=("$category")
done

# If no categories found, exit
if [ ${#categories[@]} -eq 0 ]; then
    echo "No categories found in $prompts_directory."
    exit 1
fi

if [ -n "$category_name" ]; then
    category_exists=false
    for cat in "${categories[@]}"; do
        if [[ "$cat" == "$category_name" ]]; then
            category_exists=true
            break
        fi
    done

    if [ "$category_exists" = false ]; then
        echo "Invalid category name."
        exit 1
    fi
    category="$category_name"
else
    # List available categories for selection
    echo "Available prompt directories:"
    for i in "${!categories[@]}"; do
        echo "$((i+1)). ${categories[$i]}"
    done

    read -p "Select a category by name: " category_name

    category_exists=false
    for cat in "${categories[@]}"; do
        if [[ "$cat" == "$category_name" ]]; then
            category_exists=true
            break
        fi
    done

    if [ "$category_exists" = false ]; then
        echo "Invalid selection."
        exit 1
    fi

    category="$category_name"
fi

sites=()
for prompts_file in "$prompts_directory/$category"/*.txt; do
    site=$(basename "$prompts_file" ".txt")
    sites+=("$site")
done

if [ ${#sites[@]} -eq 0 ]; then
    echo "No sites with prompts files found."
    exit 1
fi

for site in "${sites[@]}"; do
    prompts_file="$prompts_directory/$category/${site}.txt"

    echo "Processing $prompts_file"

    if [ -f "$prompts_file" ]; then
        mapfile -t tasks < <(tail -n +2 "$prompts_file")
        if [ ${#tasks[@]} -gt 0 ]; then
            url=$(head -n 1 "$prompts_file")
            echo "URL: $url"
            
            # Loop through each task
            for task in "${tasks[@]}"; do
                echo "Running task: $task"
                
                if [ "$virtual" = true ]; then
                    echo "Running in virtual display..."
                    xvfb-run --auto-servernum --server-args='-screen 0 1920x1080x24' \
                        python3 -m collector.main "$agent_method" --site "$url" --task "$task" \
                        --timeout "$timeout" --site-category "$category" "$@"
                else
                    python3 -m collector.main "$agent_method" --site "$url" --task "$task" \
                        --timeout "$timeout" --site-category "$category" "$@"
                fi
            done

        else
            echo "No tasks found in $prompts_file"
        fi
    else
        echo "No prompts file found for $site"
    fi
done

echo "All tasks completed."
