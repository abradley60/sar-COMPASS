#!/bin/bash

# Check if the scene list file is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <scene_list_file>"
    exit 1
fi

# Take the scene list file as an argument
scene_list_file="$1"

# Run allocate_scene_to_container.py to generate a list of scenes allocated to the container
python3 allocate_scene_to_container.py "$scene_list_file" > scene_list_subset.txt

# Loop through each scene in the list from the generated subset
while IFS= read -r scene; do
    python3 modify_config.py ${scene}

    # Process the scene and output memory profiling to a log file
    /usr/bin/time -v -o "/data/logs/${scene}_memory_profiling.txt" python3 main.py -c "${scene}_config.yaml"
    
    # Upload the generated logs
    # python3 upload_logs.py -c "${scene}_config.yaml"
done < scene_list_subset.txt

# Clean up by deleting the scene list file
rm scene_list_subset.txt
