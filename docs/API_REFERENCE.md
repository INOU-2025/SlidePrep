# Web API Reference

The FastAPI backend exposes a REST API under `/jobs`. All endpoints are available at `http://localhost:8000` when running with Docker Compose.

---

## `POST /jobs` — Submit a processing job

Uploads tile files and starts an async pipeline run. Accepts `multipart/form-data`.

### Form fields

| Field | Type | Default | Description |
|---|---|---|---|
| `files` | file(s) | *(required)* | One or more tile image files, or a single `.zip` archive containing tiles. Zip files are extracted automatically; `__MACOSX` metadata is removed. |
| `clean_grid` | string | `"true"` | Set to `"false"` to skip grid removal (passthrough mode — equivalent to CLI `--no-grid`). |
| `grid_width` | string | *(from config)* | Number of tile columns. Overrides `stitching.width` in the server config. |
| `grid_height` | string | *(from config)* | Number of tile rows. Overrides `stitching.height`. |
| `overlap` | string | *(from config)* | Fractional tile overlap (0–1). Overrides `stitching.overlap`. |
| `pixel_size` | string | *(from config)* | Physical pixel size in µm. Overrides `stitching.pixel_size`. |
| `direction` | string | *(from config)* | Raster scan direction (`"horizontal"` or `"vertical"`). Overrides `stitching.direction`. |
| `suffix_filter` | string | *(from config)* | Only process tiles whose filename (without extension) ends with this string. Overrides `general.suffix_filter`. |
| `grid_angle` | string | *(from config)* | Grid rotation angle in degrees. Sets `grid_detection.angles` to `[grid_angle]`. |
| `detection_threshold` | string | *(from config)* | Template-matching score threshold (0–1). Overrides `grid_detection.threshold`. |

### Response — `JobResponse`

```json
{ "job_id": "uuid", "status": "QUEUED", "message": "Job submitted successfully" }
```

---

## `GET /jobs/{job_id}` — Poll job status

### Response — `JobStatus`

```json
{
  "job_id": "uuid",
  "status": "PROCESSING",     // QUEUED | PROCESSING | SUCCESS | FAILURE
  "message": "Processing 3/9: inpainting",
  "progress": 40,             // 0–100 (only during PROCESSING)
  "result_url": null,         // set on SUCCESS: path to the .dzi file
  "thumbnail_url": null,      // set on SUCCESS: path to the thumbnail tile
  "width": null,              // WSI width in pixels (set on SUCCESS)
  "height": null,             // WSI height in pixels (set on SUCCESS)
  "tile_count": null,         // total DZI tiles generated (set on SUCCESS)
  "error": null               // error message (set on FAILURE)
}
```

When `status` is `"SUCCESS"`, `result_url` points to a Deep Zoom Image (`.dzi`) served from `/results/`. Load it into an OpenSeadragon viewer via `tileSources: result_url`.

---

## `GET /jobs/{job_id}/export` — Download raw OME-TIFF

Returns the Ashlar-generated OME-TIFF as `application/tiff`. The file is served with the filename `{job_id}_slide.ome.tif`.

Returns `404` if the job is still processing or has not yet produced an OME-TIFF.

---

## `DELETE /jobs/{job_id}` — Delete a job

Removes the uploaded tiles, processed tiles, OME-TIFF, DZI tiles, and thumbnail from disk.

```json
{ "message": "Job deleted successfully" }
```

---

## Web pipeline stages

When a job runs, the worker executes these stages in order:

| Stage | Detail |
|---|---|
| Upload extraction | Zip archives are unpacked; `__MACOSX` directories are stripped |
| Tile processing | Each tile is run through the configured pipeline steps (binarization → grid detection → refinement → mask → inpainting → conversion), or skipped if `clean_grid=false` |
| Stitching | Processed tiles are assembled into an OME-TIFF via Ashlar (`service.stitch()`) |
| DZI generation | `vips dzsave` converts the OME-TIFF into Deep Zoom Image tiles for the OpenSeadragon viewer |

`progress` in `GET /jobs/{job_id}` tracks 0–80% across tile processing; stitching and DZI generation account for the remainder.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `SLIDEPREP_CONFIG` | `config/production.json` | Server-side config file used as the base for every job. Per-job form fields override specific keys at runtime. |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker URL |
| `CORS_ORIGINS` | `http://localhost` | Comma-separated allowed origins |
