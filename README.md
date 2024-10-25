Setup notes
conda activate compass_isce3
conda install -c conda-forge compass
conda install rasterio
conda install -c avalentino -c conda-forge s1etad
pip install requirements.txt

need to create burst db - https://github.com/opera-adt/burst_db
potentially move this inside a docker container in a fixed location