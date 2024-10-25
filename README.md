

Notes
conda activate compass_isce3
conda install -c conda-forge compass
conda install rasterio
conda install -c avalentino -c conda-forge s1etad


pip install requirements.txt


docker build -t compass-orc:latest .
docker run --volume /home/ubuntu/sar-COMPASS-data:/data -it compass-orc:latest bash
cd /home/compass_user/scripts
python3 -m pdb main.py -c config.yaml


modify config.yaml and put data in /data