### Instructions to run a multi-container setup

1. Update `sar_scene_list.txt` with your desired Sentinel-1 scenes.

2. Build the container with a tag.

    ```
    docker build -t compass-orc:latest .
    ```

3. Leave existing nodes.

    ```
    docker swarm leave --force
    ```

4. Inititate a new swarm.

    ```
    docker swarm init
    ```

5. Deploy a multi-container setup. Specify the number of wanted containers in the `num_replicas` and `replicas` fields in the `docker-compose.yaml`. This can be less than or equal to the number of scenes in your scene list.

    ```
    docker stack deploy -c docker-compose.yaml sar_test
    ```

#### Optional

6. View containers.

    ```
    docker ps
    ```

7. Copy the container ID or name (recommended since the container IDs seem to change in docker swarm) from above to view the logs. The --follow or -f parameter is to enable real-time logs.

    ```
    docker logs -f container_name
    ```