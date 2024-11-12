import os
import json
from datetime import datetime
import yaml

def update_timing_file(key, time, path, replace=False):
    """Update the timing json at specified path. Creates if doesn't exists

    Args:
        key (str): key for the timing dict
        time (floar): time in seconds
        path (str): path to the timing file
        replace (bool, optional): Replace a value in the file if it already exists. Defaults to False.
    """
    if os.path.exists(path):
        with open(path, 'r') as fp:
            timing = json.load(fp)
    else:
        timing = {}
    if ((key not in timing) or replace):
        timing[key] = time
    # update total
    total_t = sum([timing[k] for k in timing.keys() if k != 'Total'])
    timing['Total'] = total_t
    with open(path, 'w') as fp:
        json.dump(timing, fp)

def get_scene_name(config):
    # read in the config for on the fly (otf) processing
    with open(config, 'r', encoding='utf8') as fin:
        main_config = yaml.safe_load(fin.read())
    return main_config['scenes'][0]

def get_unique_log_filename(scene_name):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{scene_name}_{timestamp}.log"