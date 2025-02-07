
# Dockerised Flask/React application

## Requirements

- Docker Compose version v2.32.1 

## Deployment

From the root directory of the codebase (folder containing ```docker-compose.yml```). To build the images, and run the containers in a detached manner using a single line of code:

```(sudo) docker-compose up -d --build```

This will bring the application online, but with empty databases (no registered users) so no access will be possible. To seed the database, run:

```(sudo) docker-compose exec web python3 manage.py seed_db```

This command runs the seed_db method contained at ```services/web/manage.py```, which allows interaction with the already running backend Flask server.

To monitor server activity, real time logs can be printed to console by:

```(sudo) docker-compose logs -f```

To stop deployment:

```(sudo) docker-compose down```

### Git ignored files

This repository does not contain the ```services/web/data/``` folder, which is were all sequencing and post-processing files would be stored. Hence, if deployed, no data will be available.

### Launching the server to a specific web domain

I have made so that ```docker-compose.yml``` receives the environment variables ```$WEBSITE_NAME``` and ```$WEBSITE_ROOT``` and propagates it internally to the services in question. Every other route should be relative within the application, with internal communication between the services. Therefore, only changes to docker-compose.yml should be required if deploying to a website other than ukneqastest.com (I might be wrong). 

To add https protocol, new locations and ports must be specified at ```services/nginx/```, to redirect traffic to the secure port. Speaking about ports, the docker-compose.yml specifies what ports the services are using, if these must be changed, the code of each service should be reviewed.



