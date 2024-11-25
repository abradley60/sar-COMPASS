from utils.utils import get_scene_name
from utils.aws import upload_file
import logging
import argparse
import os
import yaml
import glob

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def run_process(config):
    # Read the config for on-the-fly (otf) processing
    with open(config, 'r', encoding='utf8') as fin:
        main_config = yaml.safe_load(fin.read())

    # Read AWS credentials and set as environment variables
    logging.info(f'Setting AWS credentials from: {main_config["aws_credentials"]}')
    with open(main_config['aws_credentials'], "r", encoding='utf8') as f:
        aws_cfg = yaml.safe_load(f.read())
        for k in aws_cfg.keys():
            logging.info(f'Setting {k}')
            os.environ[k] = aws_cfg[k]

    logging.info("AWS environment variables set successfully.")
    
    # Get scene name and other parameters
    SCENE_PREFIX = '' if main_config["scene_prefix"] is None else main_config["scene_prefix"]
    S3_BUCKET_FOLDER = '' if main_config["s3_bucket_folder"] is None else main_config["s3_bucket_folder"]
    scene_list = [line.strip() for line in open('/home/ubuntu/sar-COMPASS/sar_scene_list.txt')]

    for scene_name in scene_list:   
        bucket_folder = os.path.join(
            S3_BUCKET_FOLDER,
            main_config["software"],
            main_config['dem_type'],
            f'{SCENE_PREFIX}{scene_name}'
        )

        # Find all files matching the scene name
        files_to_upload = glob.glob(f"{scene_name}*")

        if not files_to_upload:
            logging.warning(f"No files found matching the scene name: {scene_name}")
            return

        # Upload each matching file
        for file_path in files_to_upload:
            file_name = os.path.basename(file_path)
            logging.info(f'Uploading file {file_path} to {bucket_folder}')
            upload_file(
                file_path,
                bucket=main_config['s3_bucket'],
                object_name=os.path.join(bucket_folder, file_name),
            )

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--config", "-c", help="path to config.yml", required=True, type=str)
        args = parser.parse_args()

        run_process(args.config)
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
