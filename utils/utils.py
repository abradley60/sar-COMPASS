import os
import json

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