

# RSV NEQAS - a dockerised Flask/React application

## Requirements

- Docker Compose version v2.32.1 

## App architecture

The application's file structure is determined by the services defined in `docker-compose.yml`.  Both production and development versions utilize all services, with the primary distinction being that the development version skips the production build (`npm run build`), reducing deployment time.

Some services do not require custom code as they are pre-built Docker images pulled from Docker Hub. These services do not require further modifications. The services that are built from custom code include:

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

Detailed document for the Flask backend (`web` service) and client `frontend` are available, see [**Auto-generating documentation with Sphinx**](#auto-generating-documentation-with-sphinx) for more details. Both follow standard development practices. The `nginx` service is also fairly standard.

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

### Data volume

This repository does not contain the ```services/web/data/``` folder which is used to store sequencing and post-processing files. As such, if you deploy immediately after cloning the repository, no data will be available, and dynamic seeding of the databases will fail.

The ```services/web/data/``` folder is ignored by both Git and Docker, but it is mounted as a volume for use by the application. This folder must be populated before deployment. Any file uploads or processing within the containerised application will be reflected in this volume in real-time, ensuring that data retrieval works as if the application were not containerised.

### Launching the server to a specific web domain

I have made it so that ```docker-compose.yml``` receives the environment variables ```$WEBSITE_NAME``` and ```$WEBSITE_ROOT``` and propagates them internally to the services in question. Every other route should be relative within the application, with internal communication between the services. Therefore, only changes to docker-compose.yml should be required if deploying to a website other than ukneqastest.com. There is one exception; using a domain subdirectory such as *website.com/rsv*. In that case, refer to the next section.

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

# MOST IMPORTANT TO DOs

- Update web application to reflect changes to output docx/pdf reports.
- Proxy the URLs of bams and such files that are consumed by JBrowse2, for example with URLs saved to database that expire every 4 hours.
- Make the admin's "Download all" a background task launched on Redis, as it takes long to complete: there is a timeout for the frontend and it does not return it. Nevertheless, reports can be found at web/project/static/reports.
- Temporary files like images should preferrably be saved to these locations as well.
- 'Settings' and 'About' views should have something meaningful, possibly a letterbox for user ideas/requests (saved to database).
- Websocket for the notification system needs debugging in production.
- Reverse proxy nginx needs configuration for https when rerouted.