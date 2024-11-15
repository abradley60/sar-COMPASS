import yaml
import os
import sys
import shutil

def modify_yaml(scene_name):
    # Path to the original config.yaml
    original_config_path = 'config.yaml'

    # Check if the original config.yaml exists
    if not os.path.exists(original_config_path):
        print(f"Error: The file {original_config_path} does not exist.")
        return

    # Load the original YAML file
    with open(original_config_path, 'r') as file:
        config = yaml.safe_load(file)

    # Modify the 'scene' key to the given scene name
    config['scene'] = scene_name

    # New file name with the scene name added
    new_config_name = f"{scene_name}_config.yaml"

    # Save the modified YAML to a new file
    with open(new_config_name, 'w') as file:
        yaml.dump(config, file, default_flow_style=False)

    print(f"Config file modified and saved as {new_config_name}")

# Main entry point of the script
if __name__ == "__main__":
    # Check if scene name is passed as argument
    if len(sys.argv) != 2:
        print("Usage: python modify_yaml.py <scenename>")
        sys.exit(1)

    scene_name = sys.argv[1]
    modify_yaml(scene_name)
