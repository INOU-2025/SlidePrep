# SlidePrep Angular Client

Angular 21 frontend for the SlidePrep web interface. Built with standalone components and served by the nginx container in the Docker Compose stack — no Node.js installation required for production use.

## Architecture

```
src/app/
├── core/services/
│   ├── api.service.ts        # HTTP client for the FastAPI backend (/jobs endpoints)
│   └── project.service.ts    # In-memory slide state and selection management
├── shared/top-bar/           # App bar (switches between Home and Workspace modes)
└── features/
    ├── startup/              # Slide list + two-step create-slide modal
    └── workspace/            # Deep-zoom viewer (OpenSeadragon)
```

### Key flows

- **Startup view**: lists existing slides. The "New slide" modal collects tile files (or a zip archive) in step 1, then stitching parameters (`width`, `height`, `overlap`, `pixel_size`, `direction`) and processing options (`clean_grid`, `suffix_filter`, `grid_angle`, `detection_threshold`) in step 2. On submit it calls `POST /jobs`.
- **Workspace view**: polls `GET /jobs/{id}` until the job reaches `SUCCESS`, then loads the resulting DZI into an OpenSeadragon viewer for deep-zoom navigation.
- **Export**: calls `GET /jobs/{id}/export` to download the raw OME-TIFF.

## Development setup

The backend stack runs in Docker; only the Angular dev server needs Node.js locally.

```bash
# 1. Start backend (Redis, FastAPI, Celery worker)
docker compose up redis api worker

# 2. Serve the Angular app with live reload
cd client
npm install
ng serve          # http://localhost:4200
```

Set `CORS_ORIGINS=http://localhost:4200` on the `api` service (or in a `.env` file at the repo root) when using the Angular dev server instead of the nginx container.

## Production build

The pre-built output committed under `client/dist/` is served directly by the nginx container — you do not need to rebuild unless you change the frontend source.

To rebuild:

```bash
cd client
npm install
ng build          # output lands in dist/
```

Then rebuild the Docker image to pick up the new dist:

```bash
docker compose up --build
```

## Running unit tests

```bash
cd client
ng test
```
