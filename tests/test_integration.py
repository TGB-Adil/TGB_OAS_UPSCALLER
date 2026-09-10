import sqlite3
import os
from tgb_oas_upscaller import OASModule


def main():
    
    api_key = os.environ["TGB_OAS_API_KEY"]

    connection = sqlite3.connect(
        "GeoGrimUltraLite16.db"
    )

    module = OASModule(
        api_key=api_key,
        connector_db_conn=connection,
    )

    module.upscale(
        connector_table="Connector_SOBS_OAS",
        source_size="10m",
        as_col_name="SOBS_oas_code",
    )

    connection.close()


if __name__ == "__main__":
    main()
    
