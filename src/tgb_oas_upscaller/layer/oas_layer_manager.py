import re
import sqlite3


class OASLayerManager:

    ORDERED_SIZES = [
        "500km",
        "100km",
        "50km",
        "10km",
        "5km",
        "1km",
        "500m",
        "100m",
        "50m",
        "10m",
        "5m",
        "1m",
    ]

    SIZE_MAP = {
        "500km": 500000,
        "100km": 100000,
        "50km": 50000,
        "10km": 10000,
        "5km": 5000,
        "1km": 1000,
        "500m": 500,
        "100m": 100,
        "50m": 50,
        "10m": 10,
        "5m": 5,
        "1m": 1,
    }

    def __init__(
        self,
        connection: sqlite3.Connection
    ):
        self.connection = connection
        self.connection.row_factory = sqlite3.Row

    def build_all_layers(self) -> None:

        for size in self.ORDERED_SIZES:

            table_name = self.get_table_for_size(
                size
            )

            self.connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{table_name}" (
                    oas_code       TEXT PRIMARY KEY,
                    as_cx_wgs      REAL,
                    as_cy_wgs      REAL,
                    as_blx_wgs     REAL,
                    as_bly_wgs     REAL,
                    as_tlx_wgs     REAL,
                    as_tly_wgs     REAL,
                    as_trx_wgs     REAL,
                    as_try_wgs     REAL,
                    as_brx_wgs     REAL,
                    as_bry_wgs     REAL,
                    as_code_parent TEXT
                )
                """
            )

        self.connection.commit()

        print(
            "[UPSCALE] OAS layer tables ready"
        )

    def get_layer_index(
        self,
        size: str
    ) -> int:

        self._validate_size(size)

        return (
            self.ORDERED_SIZES.index(size)
            + 1
        )

    def get_table_for_size(
        self,
        size: str
    ) -> str:

        index = self.get_layer_index(
            size
        )

        return f"OAS_L{index}_{size}"

    def get_size_in_meters(
        self,
        size: str
    ) -> int:

        self._validate_size(size)

        return self.SIZE_MAP[size]

    def get_parent_size(
        self,
        size: str
    ) -> str | None:

        self._validate_size(size)

        index = self.ORDERED_SIZES.index(
            size
        )

        if index == 0:
            return None

        return self.ORDERED_SIZES[
            index - 1
        ]

    def get_child_size(
        self,
        size: str
    ) -> str | None:

        self._validate_size(size)

        index = self.ORDERED_SIZES.index(
            size
        )

        if index == len(
            self.ORDERED_SIZES
        ) - 1:
            return None

        return self.ORDERED_SIZES[
            index + 1
        ]

    def get_parent_sizes(
        self,
        size: str
    ) -> list[str]:

        self._validate_size(size)

        index = self.ORDERED_SIZES.index(
            size
        )

        return self.ORDERED_SIZES[
            :index
        ]

    def get_sizes_from_parent_to_child(
        self,
        source_size: str
    ) -> list[str]:

        self._validate_size(
            source_size
        )

        index = self.ORDERED_SIZES.index(
            source_size
        )

        return self.ORDERED_SIZES[
            index:
        ]

    def get_size_from_code(
        self,
        as_code: str
    ) -> str:

        match = re.match(
            r"TGB\d+_([\d]+km|[\d]+m{1,2})X",
            as_code
        )

        if not match:
            raise ValueError(
                f"Cannot extract size from: {as_code}"
            )

        return match.group(1)

    def _validate_size(
        self,
        size: str
    ) -> None:

        if size not in self.ORDERED_SIZES:

            raise ValueError(
                f"Unsupported OAS size: {size}"
            )
