### Instructions to run the docker container interactively

Build the container with a tag.

`docker build -t compass-orc:latest .`

Run the container in interactive mode, mounting your local data folder to the one inside the Docker container.

`docker run --volume /home/ubuntu/sar-COMPASS-data:/data -it compass-orc:latest bash`

Navigate to the scripts folder inside the Docker container.

`cd /home/compass_user/scripts` 

Run the script in debugging mode.

`python3 -m pdb main.py -c config.yaml` 

Optionally, run the script with memory profiling.

`/usr/bin/time -v -o /data/logs/output_memory_profiling.txt python3 main.py -c config.yaml`

Upload the logs to the S3 bucket.

`python3 upload_logs.py -c config.yaml`

### Extra installation notes
`conda install -c avalentino -c conda-forge s1etad`

`pip install requirements.txt`