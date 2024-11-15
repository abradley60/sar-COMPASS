import os
import argparse

# Set up argument parsing to accept a scene list file as a command-line argument
parser = argparse.ArgumentParser(description="Allocate and print subset of scenes.")
parser.add_argument("scene_list_file", help="Path to the scene list text file")
args = parser.parse_args()

# Get task ID and number of replicas from environment variables
task_id = int(os.getenv('task_id'))  # Get the task ID (1-based)
i = task_id - 1  # Convert to 0-based index for Python
n = int(os.getenv('num_replicas'))  # Get the total number of replicas

# Read scene list from the provided text file and strip newlines and extra spaces
scene_list = []
with open(args.scene_list_file, 'r') as file:
    for line in file:
        scene_list.append(line.strip())

# Divide the scene list among tasks
l = len(scene_list)
q, r = divmod(l, n)  # Calculate how many scenes per task and the remainder

# Calculate the start and end indices for the current task
start_idx = i * q + min(i, r)
end_idx = start_idx + q + (1 if i < r else 0)

# Allocate the subset of scenes for the current task
allocation = scene_list[start_idx:end_idx]

# Print the allocated subset of scenes, each on a new line
for scene in allocation:
    print(scene)
