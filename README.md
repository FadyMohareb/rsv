

# Dockerised Flask/React application

## Requirements

- Docker Compose version v2.32.1 

## App architecture

The app's file structure can be inferred from the services present in `docker-compose.yml`.  Both production and development versions use all services, the only difference is the development version does not produce the optimised production build (`npm run build`), saving deployment time. 

Some of these services do not require any codebase, as they are Docker images pulled from the Hub and whose functionalities require no further modification. The services that are built from custom code are:

```
docker-compose.yml
services/
│── web/
│   │── Dockerfile
│   │── manage.py
│   │── project/
│   │   │── __init__.py
│   │   │── admin.py
│   │   │── authentication.py
│   │   │── config.py
│   │   │── data.py
│   │   │── notifications.py
│   │   │── upload.py
│   │   │── utils/
│   │   │   │── docx.py
│   │   │   │── report_parser.py
│   │   │   │── sql_models.py
│   │── docs/
│   │── data/
│
│── frontend/
│   │── Dockerfile
│   │── package.json
│   │── src/
│   │   │── App.js
│   │   │── index.js
│   │   │── components/
│   │   │   │── About.js
│   │   │   │── Home.js
│   │   │   │── DataView.js
│   │   │   │── DistributionManager.js
│   │   │   │── DownloadButton.js
│   │   │   │── SamplePlot.js
│   │   │   │── SeqPlot.js
│   │   │   │── Settings.js
│   │   │   │── Toolbar.js
│   │   │   │── Upload.js
│   │── docs/
│
│── nginx/
│   │── Dockerfile
│   │── nginx.conf
│   │── default.conf
│
│── rq-dashboard/
│   │── Dockerfile
```

Detailed document for the Flask backend (`web` service) and client `frontend` are available, see [**Auto-generating documentation with Sphinx**](#auto-generating-documentation-with-sphinx) for more details. Both follow standard practices. The `nginx` service is very standard as well.

## Deployment

From the root directory of the codebase (folder containing ```docker-compose.yml```). To build the images, and run the containers in a detached manner using a single line of code:

```(sudo) docker-compose up -d --build```

This will bring the application online, but with empty databases (no registered users) so no access will be possible. To seed the database, run:

```(sudo) docker-compose exec web python3 manage.py seed_db```

This command runs the seed_db method contained at ```services/web/manage.py```, which allows interaction with the already running backend Flask server. Commands can even be added/modified at runtime.

To monitor server activity, real time logs can be printed to console by:

```(sudo) docker-compose logs -f```

To stop deployment:

```(sudo) docker-compose down```

### Git ignored files

This repository does not contain the ```services/web/data/``` folder, which is were all sequencing and post-processing files would be stored. Hence, if deployed, no data will be available and dynamic seeding of databases will fail.

### Launching the server to a specific web domain

I have made so that ```docker-compose.yml``` receives the environment variables ```$WEBSITE_NAME``` and ```$WEBSITE_ROOT``` and propagates it internally to the services in question. Every other route should be relative within the application, with internal communication between the services. Therefore, only changes to docker-compose.yml should be required if deploying to a website other than ukneqastest.com. There is one exception; using a domain subdirectory such as *website.com/rsv*. In that case, refer to the next section.

To add https protocol, new locations and ports must be specified at ```services/nginx/```, to redirect traffic to the secure port. Speaking about ports, the docker-compose.yml specifies what ports the services are using.

### Subdirectory web domain URLs

If the app must be served from a domain subdirectory, for example *elvis.cranfield.ac.uk/rsv*, changes required are:

- **docker-compose.yml:** set environment variables.
- **frontend:** modify the homepage route in *package.json*.
- **frontend:** modify *.env* environment variable.
- **nginx:** prepend subdirectory to server locations in *default.conf*.

### Auto-generating documentation with Sphinx

Once the services are all deployed, run:

```(sudo) docker-compose exec frontend npm run doc```
```(sudo) docker-compose exec web python3 manage.py build_docs```

This will create the documentation HTMLs in `services/web/project/docs/build/html` for both the backend using Sphinx. Start navigating via the `index.html`.

For the frontend documentation, JSDoc is preferred over Sphinx, JSDoc HTMLs are found at `services/frontend/docs`. TO DO: these could be improved.
