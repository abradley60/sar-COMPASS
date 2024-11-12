import yaml
import argparse
import os
import asf_search as asf
from eof.download import download_eofs
import logging
import zipfile
from shapely.geometry import Polygon
import time
from dem_stitcher import stitch_dem
import subprocess
import rasterio
from datetime import datetime
import shutil

from utils.utils import update_timing_file
#from utils.etad import *
from utils.raster import *
from utils.aws import upload_file,upload_files_in_folder

def get_scene_name(config):
    # read in the config for on the fly (otf) processing
    with open(config, 'r', encoding='utf8') as fin:
        main_config = yaml.safe_load(fin.read())
    return main_config['scenes'][0]

def get_unique_log_filename(scene_name):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{scene_name}_{timestamp}.log"

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

os.makedirs('/data/logs', exist_ok=True)

def run_process(config):
    """main process to download data and produce CSLC's
    based on a list of products.

    Args:
        config (str): path to the config file
    """

    scene_name = get_scene_name(config)  # Get scene name from config
    fh = logging.FileHandler(f"/data/logs/{get_unique_log_filename(scene_name)}")
    logger = logging.getLogger()
    logger.addHandler(fh)

    t_start = time.time()
    # define success / failure tracker
    success = {'COMPASS-ISCE3' : []}
    failed = {'COMPASS-ISCE3' : []}

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

    # make the timing file
    timing = {}
    t0 = time.time()
    TIMING_FILE = main_config['scenes'][0] + '_timing.json'
    TIMING_FILE_PATH = os.path.join(main_config['COMPASS_output_folder'],TIMING_FILE)

    # make lists to track downloaded files
    CONFIG_SAFE_FILE_PATH = []
    CONFIG_ORBIT_FILE_PATH = []
    asf_results_list = []

    logging.info(f'PROCESS 1: Download Scene and Orbits')
    # loop through the list of scenes
    # download the scene and orbit files
    for i, scene in enumerate(main_config['scenes']):
        
        # add the scene name to the out folder
        OUT_FOLDER = main_config['COMPASS_output_folder']
        SCENE_OUT_FOLDER = os.path.join(OUT_FOLDER,scene)
        os.makedirs(SCENE_OUT_FOLDER, exist_ok=True)

        logging.info(f'downloading scene {i+1} of {len(main_config["scenes"])} : {scene}')
        # search for the scene in asf
        logging.info(f'searching asf for scene...')
        asf.constants.CMR_TIMEOUT = 45
        logging.debug(f'CMR will timeout in {asf.constants.CMR_TIMEOUT}s')
        asf_results = asf.granule_search([scene], asf.ASFSearchOptions(processingLevel='SLC'))
        
        if len(asf_results) > 0:
            logging.info(f'scene found')
            asf_result = asf_results[0]
            asf_results_list.append(asf_result)
        else:
            logging.error(f'scene not found : {scene}')
            run_success = False
            failed['COMPASS-rtc'].append(scene)
            continue
        
        # read in credentials to download from ASF
        logging.info(f'setting earthdata credentials from: {main_config["earthdata_credentials"]}')
        with open(main_config['earthdata_credentials'], "r", encoding='utf8') as f:
            earthdata_cfg = yaml.safe_load(f.read())
            earthdata_uid = earthdata_cfg['login']
            earthdata_pswd = earthdata_cfg['password']
        
        # download scene
        logging.info(f'downloading scene')
        session = asf.ASFSession()
        session.auth_with_creds(earthdata_uid,earthdata_pswd)
        SCENE_NAME = asf_result.__dict__['umm']['GranuleUR'].split('-')[0]
        POLARIZATION = asf_result.properties['polarization']
        BEAMMODE = asf_result.properties['beamModeType']
        POLARIZATION_TYPE = 'dual-pol' if len(POLARIZATION) > 2 else 'co-pol' # string for template value
        SCENE_DOWNLOAD_FOLDER = main_config['scene_folder']
        os.makedirs(SCENE_DOWNLOAD_FOLDER, exist_ok=True)
        scene_zip = os.path.join(SCENE_DOWNLOAD_FOLDER, SCENE_NAME + '.zip')
        asf_result.download(path=SCENE_DOWNLOAD_FOLDER, session=session)
            
        # unzip scene
        ORIGINAL_SAFE_PATH = scene_zip.replace(".zip",".SAFE")
        if (main_config['unzip_scene'] or main_config['apply_ETAD']) and not os.path.exists(ORIGINAL_SAFE_PATH): 
            logging.info(f'unzipping scene to {ORIGINAL_SAFE_PATH}')     
            with zipfile.ZipFile(scene_zip, 'r') as zip_ref:
                zip_ref.extractall(SCENE_DOWNLOAD_FOLDER)

        # apply the ETAD corrections to the SLC
        if main_config['apply_ETAD']:
            logging.info('Applying ETAD corrections')
            logging.info(f'loading copernicus credentials from: {main_config["copernicus_credentials"]}')
            with open(main_config['copernicus_credentials'], "r", encoding='utf8') as f:
                copernicus_cfg = yaml.safe_load(f.read())
                copernicus_uid = copernicus_cfg['login']
                copernicus_pswd = copernicus_cfg['password']
            etad_path = download_scene_etad(
                SCENE_NAME, 
                copernicus_uid, 
                copernicus_pswd, etad_dir=main_config['ETAD_folder'])
            ETAD_SCENE_FOLDER = f'{main_config["scene_folder"]}_ETAD'
            logging.info(f'making new directory for etad corrected slc : {ETAD_SCENE_FOLDER}')
            ETAD_SAFE_PATH = apply_etad_correction(
                ORIGINAL_SAFE_PATH, 
                etad_path, 
                out_dir=ETAD_SCENE_FOLDER,
                nthreads=main_config['gdal_threads'])
        
        # set as the safe file for processing
        SAFE_PATH = ORIGINAL_SAFE_PATH if not main_config['apply_ETAD'] else ETAD_SAFE_PATH
        CONFIG_SAFE_FILE_PATH.append(SAFE_PATH)

        PRECISE_ORBIT_DOWNLOAD_FOLDER = main_config['precise_orbit_folder']
        RESTITUDED_ORBIT_DOWNLOAD_FOLDER = main_config['restituted_orbit_folder']
        os.makedirs(PRECISE_ORBIT_DOWNLOAD_FOLDER, exist_ok=True)
        os.makedirs(RESTITUDED_ORBIT_DOWNLOAD_FOLDER, exist_ok=True)

        # download orbits
        logging.info(f'downloading orbit files for scene')
        prec_orb_files = download_eofs(sentinel_file=scene_zip, 
                      save_dir=main_config['precise_orbit_folder'], 
                      orbit_type='precise',
                      asf_user=earthdata_uid,
                      asf_password=earthdata_pswd)
        if len(prec_orb_files) > 0:
            ORBIT_PATH = str(prec_orb_files[0])
            logging.info(f'using precise orbits: {ORBIT_PATH}')
        else:
            #download restituted orbits
            res_orb_files = download_eofs(sentinel_file=scene_zip, 
                          save_dir=main_config['restituted_orbit_folder'], 
                          orbit_type='restituted',
                          asf_user=earthdata_uid,
                          asf_password=earthdata_pswd,
                          )  
            ORBIT_PATH = str(res_orb_files[0])
            logging.info(f'using restituted orbits: {ORBIT_PATH}')
        
        CONFIG_ORBIT_FILE_PATH.append(ORBIT_PATH)
        
    # print(f'Downloaded {len(CONFIG_SAFE_FILE_PATH)} of {len(main_config['scenes'])} scenes')
    t1 = time.time()
    update_timing_file('Download Scene', t1 - t0, TIMING_FILE_PATH)

    # download the DEM
    # TODO make antimeridian and Antarctic compatible 
    # NOTE - Assume ALL the files in the config are covered by the same DEM
    # Get the bounds of the first DEM
    logging.info(f'PROCESS 2: Download DEM')
    scene_geom = asf_results_list[0].geometry
    scene_polygon = Polygon(scene_geom['coordinates'][0])
    scene_bounds = scene_polygon.bounds

    # if we are at high latitudes we need to correct the bounds due to the skewed box shape
    if (scene_bounds[1] < -50) or (scene_bounds[3] < -50):
        # Southern Hemisphere
        logging.info(f'Adjusting scene bounds due to warping at high latitude')
        scene_polygon = adjust_scene_poly_at_extreme_lat(scene_bounds, 4326, 3031)
        scene_bounds = scene_polygon.bounds 
        logging.info(f'Adjusted scene bounds : {scene_bounds}')
    if (scene_bounds[1] > 50) or (scene_bounds[3] > 50):
        # Northern Hemisphere
        logging.info(f'Adjusting scene bounds due to warping at high latitude')
        scene_polygon = adjust_scene_poly_at_extreme_lat(scene_bounds, 4326, 3995)
        scene_bounds = scene_polygon.bounds 
        logging.info(f'Adjusted scene bounds : {scene_bounds}')

    buffer = 0.3
    scene_bounds_buf = scene_polygon.buffer(buffer).bounds #buffered

    if main_config['dem_path'] is not None:
        # set the dem to be the one specified if supplied
        logging.info(f'using DEM path specified : {main_config["dem_path"]}')
        if not os.path.exists(main_config['dem_path']):
            raise FileExistsError(f'{main_config["dem_path"]} c')
        else:
            DEM_PATH = main_config['dem_path']
            dem_filename = os.path.basename(DEM_PATH)
            main_config['dem_folder'] = os.path.dirname(DEM_PATH) # set the dem folder
            main_config['overwrite_dem'] = False # do not overwrite dem
    else:
        # make folders and set filenames
        dem_dl_folder = os.path.join(main_config['dem_folder'],main_config['dem_type'])
        os.makedirs(dem_dl_folder, exist_ok=True)
        dem_filename = SCENE_NAME + '_dem.tif'
        DEM_PATH = os.path.join(dem_dl_folder,dem_filename)
    
    if (main_config['overwrite_dem']) or (not os.path.exists(DEM_PATH)) or (main_config['dem_path'] is None):
        logging.info(f'Downloding DEM for  bounds : {scene_bounds_buf}')
        logging.info(f'type of DEM being downloaded : {main_config["dem_type"]}')
        if 'REMA' not in str(main_config['dem_type']).upper():
            # get the DEM and geometry information
            dem_data, dem_meta = stitch_dem(scene_bounds_buf,
                            dem_name=main_config['dem_type'],
                            dst_ellipsoidal_height=True,
                            dst_area_or_point='Point',
                            merge_nodata_value=0
                            )
            # save with rasterio
            with rasterio.open(DEM_PATH, 'w', **dem_meta) as ds:
                ds.write(dem_data, 1)
                ds.update_tags(AREA_OR_POINT='Point')
            del dem_data
            logging.info(f'DEM downloaded : {DEM_PATH}')
            # save with rasterio
            logging.info(f'saving dem to {DEM_PATH}')
            with rasterio.open(DEM_PATH, 'w', **dem_meta) as ds:
                ds.write(dem_data, 1)
                ds.update_tags(AREA_OR_POINT='Point')
            del dem_data

    t2 = time.time()
    update_timing_file('Download DEM', t2 - t1, TIMING_FILE_PATH)

    # now we have downloaded all the necessary data, we can create a
    # config for the scene we want to process
    with open(main_config['COMPASS_template'], 'r') as f:
        template_text = f.read()
    # search for the strings we want to replaces
    template_text = template_text.replace('CONFIG_SAFE_FILE_PATH',
                                          str(CONFIG_SAFE_FILE_PATH[0]))
    template_text = template_text.replace('CONFIG_ORBIT_FILE_PATH',
                                          str(CONFIG_ORBIT_FILE_PATH[0]))
    if main_config['burst_ids'] is not None:
        template_text = template_text.replace('CONFIG_BURST_ID',
                                          str(main_config['burst_ids']))
    else: 
        template_text = template_text.replace('CONFIG_BURST_ID',
                                          '')
    template_text = template_text.replace('CONFIG_DEM_FILE',
                                          DEM_PATH)
    #template_text = template_text.replace('SCENE_NAME',SCENE_NAME)
    template_text = template_text.replace('CONFIG_SCRATCH_PATH',
                                            main_config['COMPASS_scratch_folder'])
    template_text = template_text.replace('CONFIG_PRODUCT_PATH',
                                            SCENE_OUT_FOLDER)
    template_text = template_text.replace('CONFIG_POLARISATION',
                                            POLARIZATION_TYPE)
    template_text = template_text.replace('CONFIG_BURST_DATABASE_FILE', 
                                          main_config['COMPASS_burst_database_file'])

    COMPASS_CONFIG_FOLDER = main_config['COMPASS_config_folder']
    os.makedirs(COMPASS_CONFIG_FOLDER, exist_ok=True)

    cProfile_path = main_config['cProfile_folder']
    os.makedirs(COMPASS_CONFIG_FOLDER, exist_ok=True)

    # name config after first scene
    COMPASS_config_name = main_config['scenes'][0] + '.yaml'
    COMPASS_config_path = os.path.join(COMPASS_CONFIG_FOLDER, COMPASS_config_name)
    with open(COMPASS_config_path, 'w') as f:
        f.write(template_text)

    # read in the config template for the RTC runs
    with open(COMPASS_config_path, 'r', encoding='utf8') as fin:
        COMPASS_rtc_cfg = yaml.safe_load(fin.read())

    logging.info(f'PROCESS 3: Generate CLSC with Compass')
    command = f"python3 -m cProfile -o {cProfile_path}/{scene_name}.prof $(type -P s1_cslc.py) --grid geo {COMPASS_config_path}"
    if not main_config['skip_COMPASS']:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Print stdout and stderr as it runs
        while True:
            # Read a line from stdout
            output = process.stdout.readline()
            if output:
                logging.info(output.strip())  # Print the output
            # Check if the process has finished
            return_code = process.poll()
            if return_code is not None:
                # Process any remaining stdout after process has finished
                for output in process.stdout.readlines():
                    logging.info(output.strip())
                # Process any remaining stderr
                for err in process.stderr.readlines():
                    logging.error(err.strip())
                break
    else:
        logging.info(f'PROCESS 3: Skipping COMPASS ("skip_COMPASS"==True)')
    
    # check if the final products exist, indicating success 
    t3 = time.time()
    update_timing_file('RTC Processing', t3 - t2, TIMING_FILE_PATH)
            
    # push to S3
    if main_config['push_to_s3']:
        logging.info(f'PROCESS 3: Push results to S3 bucket')
        # see if any prefix or additional bucket path is needed
        SCENE_PREFIX = '' if main_config["scene_prefix"] == None else main_config["scene_prefix"]
        S3_BUCKET_FOLDER = '' if main_config["s3_bucket_folder"] == None else main_config["s3_bucket_folder"]
        bucket_folder = os.path.join(
            S3_BUCKET_FOLDER,
            main_config["software"],
            main_config['dem_type'],
            f'CRS',
            f'{SCENE_PREFIX}{SCENE_NAME}')
        # upload output files
        upload_files_in_folder(
            SCENE_OUT_FOLDER,
            main_config['s3_bucket'],
            bucket_folder,
        )
        # upload DEM
        if main_config['upload_dem']:
            bucket_path = os.path.join(bucket_folder,dem_filename)
            logging.info(f'Uploading file: {DEM_PATH}')
            upload_file(DEM_PATH, 
                        bucket=main_config['s3_bucket'], 
                        object_name=bucket_path)
        # upload yaml
        bucket_path = os.path.join(bucket_folder,dem_filename)
        logging.info(f'Uploading file: {DEM_PATH}')
        upload_file(COMPASS_config_path, 
                    bucket=main_config['s3_bucket'], 
                    object_name=bucket_path)
                
        t4 = time.time()
        update_timing_file('S3 Upload', t4 - t3, TIMING_FILE_PATH)
<<<<<<< HEAD
=======

>>>>>>> origin/main
        if main_config['delete_local_files']:
            logging.info(f'PROCESS 4: Clear files locally')
            #clear downloads
            for file_ in [scene_zip,
                        DEM_PATH,
                        ORBIT_PATH,
                        COMPASS_config_path,
                        ]:
                logging.info(f'Deleteing {file_}')
                os.remove(file_)
            logging.info(f'Clearing SAFE directory: {ORIGINAL_SAFE_PATH}')
            shutil.rmtree(ORIGINAL_SAFE_PATH)
            if main_config['apply_ETAD']:
                logging.info(f'Clearing ETAD corrected SAFE directory: {ETAD_SAFE_PATH}')
                shutil.rmtree(ETAD_SAFE_PATH)
                logging.info(f'Clearing directory: {ETAD_SAFE_PATH}')
<<<<<<< HEAD
=======

>>>>>>> origin/main
            shutil.rmtree(SCENE_OUT_FOLDER)
            shutil.rmtree(main_config['COMPASS_scratch_folder'])
            # remake the scratch folder
            os.makedirs(main_config['COMPASS_scratch_folder'])
        
        t5 = time.time()
        update_timing_file('Delete Files', t5 - t4, TIMING_FILE_PATH)

        # push timings
        if main_config['push_to_s3']:
            bucket_path = os.path.join(bucket_folder, TIMING_FILE)
            logging.info(f'Uploading file: {TIMING_FILE_PATH}')
            logging.info(f'Destination: {bucket_path}')
            upload_file(file_name=TIMING_FILE_PATH, 
                        bucket=main_config['s3_bucket'], 
                        object_name=bucket_path)
            os.remove(TIMING_FILE_PATH)
        
        # TODO push a logs file
        upload_files_in_folder(
            cProfile_path,
            main_config['s3_bucket'],
            bucket_folder,
        )        

    logging.info(f'Run complete, {len(main_config["scenes"])} scenes processed')
    logging.info(f'Elapsed time:  {((time.time() - t_start)/60)} minutes')

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", help="path to config.yml", required=True, type=str)
    args = parser.parse_args()

    run_process(args.config)