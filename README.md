# TGB OAS Upscaller

Reusable Python package for retrieving TGB OAS information and building/upscaling OAS layer hierarchies.

## Installation

```bash
pip install tgb-oas-upscaller
```

## Usage

```python
import sqlite3

from tgb_oas_upscaller import OASModule


connection = sqlite3.connect(
    "my_database.db"
)

module = OASModule(
    api_key="YOUR_TGB_API_KEY",
    connector_db_conn=connection,
)

module.upscale(
    connector_table="Connector_SOBS_OAS",
    source_size="10m",
    as_col_name="oas_code",
)

connection.close()
```

## Architecture

The package consists of:

* `OASModule` — public entry point
* `OASClient` — TGB OAS API communication
* `OASUpscaler` — OAS hierarchy and coordinate processing
* `OASLayerManager` — OAS layer/table management

The consuming application supplies the SQLite database connection.

The package does not open or manage the application's production database itself.

## Supported OAS Sizes

```text
500km
100km
50km
10km
5km
1km
500m
100m
50m
10m
5m
1m
```
