FROM opera/cslc_s1:final_0.5.5

USER root
RUN yum install -y time

USER compass_user
WORKDIR /home/compass_user/scripts/
COPY allocate_scene_to_container.py /home/compass_user/scripts/allocate_scene_to_container.py
COPY sar_2scene_list.txt /home/compass_user/scripts/sar_2scene_list.txt
COPY modify_config.py /home/compass_user/scripts/modify_config.py
COPY run.sh /home/compass_user/scripts/run.sh
COPY main.py /home/compass_user/scripts/main.py
COPY upload_logs.py /home/compass_user/scripts/upload_logs.py
COPY config.yaml /home/compass_user/scripts/config.yaml
COPY utils /home/compass_user/scripts/utils
COPY configs /home/compass_user/scripts/configs
COPY credentials /home/compass_user/scripts/credentials
RUN python3 -m pip install asf_search==8.0.0 sentineleof==0.9.5 rasterio==1.3.10
