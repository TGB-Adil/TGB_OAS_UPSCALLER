from tgb_oas_upscaller.client.oas_client import OASClient
from tgb_oas_upscaller.upscaller.oas_upscaller import OASUpscaler


class OASModule:

    def __init__(self,api_key: str,connector_db_conn,):
        
        self.oas_client = OASClient(api_key=api_key)

        self.upscaler = OASUpscaler(
            connector_db_conn=connector_db_conn,
            oas_client=self.oas_client,
        )

    def upscale(self,connector_table: str,source_size: str,as_col_name: str,) -> None:

        self.upscaler.run(
            connector_table=connector_table,
            source_size=source_size,
            as_col_name=as_col_name,
        )