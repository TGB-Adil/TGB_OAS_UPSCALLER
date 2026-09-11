import json
import time

import requests


class OASClient:

    ENDPOINT = (
        "https://dvdb.tgb.world/api/lib/"
        "s-oas-code-to-wgs84-coordinates-self-n0-acs/"
    )

    @classmethod
    def get_endpoint(cls) -> str:
        return cls.ENDPOINT
    
    
    def __init__(self,api_key: str,timeout: int = 1000):
        if not api_key or not api_key.strip():
            raise ValueError("OAS API key is required.")

        self.api_key = api_key
        self.timeout = timeout

    def get_self_details(self,areaseals: list[str]) -> list[dict]:

        if isinstance(areaseals, str):
            areaseals = [areaseals]

        payload = {
            "secret_key": self.api_key,
            "json_data": [
                {
                    "ID": idx + 1,
                    "areaseal": code
                }
                for idx, code in enumerate(areaseals)
            ]
        }

        return self._post(payload)

    def _post(self,payload: dict) -> list[dict]:

        for attempt in range(1, 4):

            try:

                response = requests.post(
                    self.ENDPOINT,
                    headers={
                        "Content-Type": "application/json"
                    },
                    data=json.dumps(payload),
                    timeout=self.timeout
                )

                response.raise_for_status()

                data = response.json()

                if isinstance(data, dict):

                    if "csv_data_result" in data:
                        return data["csv_data_result"]

                    return []

                if isinstance(data, list):
                    return data

                return []

            except Exception as e:

                print(
                    f"OAS API attempt "
                    f"{attempt}/3 failed: {e}"
                )

                if attempt < 3:
                    time.sleep(2)

        raise RuntimeError(
            "OAS API request failed after 3 attempts."
        )