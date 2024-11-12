from utils.utils import get_scene_name
from utils.aws import upload_files_in_folder
import logging
import argparse
import os
import yaml

def run_process(config):
    # read in the config for on the fly (otf) processing
    with open(config, 'r', encoding='utf8') as fin:
        main_config = yaml.safe_load(fin.read())

    # read in aws credentials and set as environ vars
    logging.info(f'setting aws credentials from : {main_config["aws_credentials"]}')
    with open(main_config['aws_credentials'], "r", encoding='utf8') as f:
        aws_cfg = yaml.safe_load(f.read())
        # set all keys as environment variables
        for k in aws_cfg.keys():
            logging.info(f'setting {k}')
            os.environ[k] = aws_cfg[k]

        SCENE_PREFIX = '' if main_config["scene_prefix"] == None else main_config["scene_prefix"]
        S3_BUCKET_FOLDER = '' if main_config["s3_bucket_folder"] == None else main_config["s3_bucket_folder"]
        scene_name = get_scene_name(config)
        cProfile_path = main_config['cProfile_folder']

        bucket_folder = os.path.join(
        S3_BUCKET_FOLDER,
        main_config["software"],
        main_config['dem_type'],
        f'CRS',
        f'{SCENE_PREFIX}{scene_name}')
       
        upload_files_in_folder(
            cProfile_path,
            main_config['s3_bucket'],
            bucket_folder,
        )        

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", help="path to config.yml", required=True, type=str)
    args = parser.parse_args()

    run_process(args.config)