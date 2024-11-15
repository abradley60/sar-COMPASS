### Instructions to run a multi-container setup

Build the container with a tag.

`docker build -t compass-orc:latest .`

Leave existing nodes.

`docker swarm leave --force`

Inititate a new swarm.

`docker swarm init`

Deploy a multi-container setup. Specify the number of wanted containers in the `num_replicas` and `replicas` fields in the `docker-compose.yaml`. This can be less than or equal to the number of scenes in your scene list.

`docker stack deploy -c docker-compose.yaml sar_test`

View containers.

`docker ps`

Copy the container ID or name (recommended since the container IDs seem to change in docker swarm) from above to view the logs. The --follow or -f parameter is to enable real-time logs.

`docker logs -f container_name`