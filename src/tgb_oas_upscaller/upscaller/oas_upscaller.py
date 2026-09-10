import re

from tgb_oas_upscaller.client.oas_client import OASClient
from tgb_oas_upscaller.layer.oas_layer_manager import OASLayerManager


class OASUpscaler:

    def __init__(
        self,
        connector_db_conn,
        oas_client: OASClient,
    ):
        self.connection = connector_db_conn
        self.oas_client = oas_client

        self.layer_manager = OASLayerManager(
            connection=connector_db_conn
        )

        self.layer_manager.build_all_layers()

    def get_parent_areaseal(
        self,
        child_areaseal: str,
        target_size: str
    ) -> str:

        match = re.match(
            r"(TGB\d+)_([\d]+km|[\d]+m{1,2})X(-?\d+)Y(-?\d+)Z\d+",
            child_areaseal,
        )

        if not match:

            raise ValueError(
                f"Cannot parse areaseal: "
                f"{child_areaseal}"
            )

        prefix, _, easting_s, northing_s = (
            match.groups()
        )

        easting = int(easting_s)
        northing = int(northing_s)

        target_mm = (
            self.layer_manager
            .get_size_in_meters(
                target_size
            )
            * 1000
        )

        parent_e = (
            easting // target_mm
        ) * target_mm

        parent_n = (
            northing // target_mm
        ) * target_mm

        return (
            f"{prefix}_{target_size}"
            f"X{parent_e}Y{parent_n}Z0"
        )

    def get_unique_oas_from_connector(
        self,
        connector_table: str,
        source_size: str,
        as_col_name: str,
    ) -> list[str]:

        layer_table = (
            self.layer_manager
            .get_table_for_size(
                source_size
            )
        )

        connector_rows = (
            self.connection.execute(
                f"""
                SELECT DISTINCT {as_col_name}
                FROM "{connector_table}"
                WHERE {as_col_name} IS NOT NULL
                """
            )
            .fetchall()
        )

        connector_codes = {
            row[0]
            for row in connector_rows
        }

        existing_rows = (
            self.connection.execute(
                f"""
                SELECT oas_code
                FROM "{layer_table}"
                """
            )
            .fetchall()
        )

        existing_codes = {
            row[0]
            for row in existing_rows
        }

        missing_codes = list(
            connector_codes - existing_codes
        )

        print(
            f"[UPSCALE] Found "
            f"{len(missing_codes)} new OAS codes "
            f"from {connector_table}"
        )

        return missing_codes

    def build_hierarchy_upwards(
        self,
        oas_codes: list[str],
        source_size: str,
    ) -> dict[str, set[str]]:

        sizes = (
            self.layer_manager.ORDERED_SIZES
        )

        source_index = sizes.index(
            source_size
        )

        hierarchy = {
            source_size: set(oas_codes)
        }

        # Move from the source layer towards
        # progressively larger OAS cells.
        #
        # Example:
        # 10m -> 50m -> 100m -> 500m -> 1km
        #       -> 5km -> ... -> 500km

        for index in range(
            source_index,
            0,
            -1
        ):

            child_size = sizes[index]
            parent_size = sizes[index - 1]

            hierarchy.setdefault(
                parent_size,
                set()
            )

            for child_oas in hierarchy[
                child_size
            ]:

                parent_oas = (
                    self.get_parent_areaseal(
                        child_oas,
                        parent_size
                    )
                )

                hierarchy[
                    parent_size
                ].add(parent_oas)

        return hierarchy


    def save_hierarchy(
        self,
        hierarchy: dict[str, set[str]]
    ) -> None:

        for size, codes in hierarchy.items():

            table_name = (
                self.layer_manager
                .get_table_for_size(
                    size
                )
            )

            print(
                f"[UPSCALE] Saving "
                f"{len(codes)} records into "
                f"{table_name}"
            )

            parent_size = (
                self.layer_manager
                .get_parent_size(
                    size
                )
            )

            rows = []

            for code in codes:

                parent = None

                if parent_size is not None:

                    parent = (
                        self.get_parent_areaseal(
                            code,
                            parent_size
                        )
                    )

                rows.append(
                    (
                        code,
                        parent
                    )
                )

            if not rows:
                continue

            self.connection.executemany(
                f"""
                INSERT OR IGNORE INTO "{table_name}"
                (
                    oas_code,
                    as_code_parent
                )
                VALUES (?, ?)
                """,
                rows,
            )

        self.connection.commit()

    def _ensure_hierarchy_for_code(
        self,
        as_code: str,
        size: str,
    ) -> None:

        current_code = as_code
        current_size = size

        parent_size = (
            self.layer_manager
            .get_parent_size(
                current_size
            )
        )

        parent_oas = None

        if parent_size is not None:

            parent_oas = (
                self.get_parent_areaseal(
                    current_code,
                    parent_size
                )
            )

        table_name = (
            self.layer_manager
            .get_table_for_size(
                current_size
            )
        )

        self.connection.execute(
            f"""
            INSERT OR IGNORE INTO "{table_name}"
            (
                oas_code,
                as_code_parent
            )
            VALUES (?, ?)
            """,
            (
                current_code,
                parent_oas
            ),
        )

        print(
            f"[UPSCALE] NEW as_code inserted: "
            f"{current_code} "
            f"(differs from sent areaseal) "
            f"→ hierarchy being built"
        )

        child_code = current_code
        child_size = current_size

        while True:

            parent_size = (
                self.layer_manager
                .get_parent_size(
                    child_size
                )
            )

            if parent_size is None:
                break

            parent_code = (
                self.get_parent_areaseal(
                    child_code,
                    parent_size
                )
            )

            grandparent_size = (
                self.layer_manager
                .get_parent_size(
                    parent_size
                )
            )

            grandparent_oas = None

            if grandparent_size is not None:

                grandparent_oas = (
                    self.get_parent_areaseal(
                        parent_code,
                        grandparent_size
                    )
                )

            parent_table = (
                self.layer_manager
                .get_table_for_size(
                    parent_size
                )
            )

            self.connection.execute(
                f"""
                INSERT OR IGNORE INTO "{parent_table}"
                (
                    oas_code,
                    as_code_parent
                )
                VALUES (?, ?)
                """,
                (
                    parent_code,
                    grandparent_oas
                ),
            )

            child_code = parent_code
            child_size = parent_size

        self.connection.commit()

    def fill_coordinates(
        self,
        batch_size: int = 10000,
    ) -> None:

        for size in (
            self.layer_manager.ORDERED_SIZES
        ):

            table_name = (
                self.layer_manager
                .get_table_for_size(
                    size
                )
            )

            rows = (
                self.connection.execute(
                    f"""
                    SELECT oas_code
                    FROM "{table_name}"
                    WHERE as_cx_wgs IS NULL
                    """
                )
                .fetchall()
            )

            oas_codes = [
                row[0]
                for row in rows
            ]

            total = len(oas_codes)

            if total == 0:
                continue

            print(
                f"[UPSCALE] "
                f"{table_name} "
                f"pending={total}"
            )

            for start in range(
                0,
                total,
                batch_size
            ):

                batch = oas_codes[
                    start:start + batch_size
                ]

                batch_no = (
                    start // batch_size
                ) + 1

                total_batches = (
                    total + batch_size - 1
                ) // batch_size

                print(
                    f"[UPSCALE] "
                    f"Batch "
                    f"{batch_no}/{total_batches}"
                )

                response = (
                    self.oas_client
                    .get_self_details(
                        batch
                    )
                )

                updates = []

                for item in response:

                    as_code = item.get(
                        "as_code"
                    )

                    areaseal = item.get(
                        "areaseal"
                    )

                    if not as_code:
                        continue

                    coord_values = (
                        item.get("as_cx_wgs"),
                        item.get("as_cy_wgs"),
                        item.get("as_blx_wgs"),
                        item.get("as_bly_wgs"),
                        item.get("as_tlx_wgs"),
                        item.get("as_tly_wgs"),
                        item.get("as_trx_wgs"),
                        item.get("as_try_wgs"),
                        item.get("as_brx_wgs"),
                        item.get("as_bry_wgs"),
                    )

                    if as_code == areaseal:

                        updates.append(
                            (
                                *coord_values,
                                as_code,
                            )
                        )

                    else:

                        print(
                            f"[UPSCALE] Edge case: "
                            f"sent={areaseal} "
                            f"got={as_code} "
                            f"— inserting new cell"
                        )

                        actual_size = (
                            self.layer_manager
                            .get_size_from_code(
                                as_code
                            )
                        )

                        self._ensure_hierarchy_for_code(
                            as_code,
                            actual_size,
                        )

                        actual_table = (
                            self.layer_manager
                            .get_table_for_size(
                                actual_size
                            )
                        )

                        self.connection.execute(
                            f"""
                            UPDATE "{actual_table}"
                            SET
                                as_cx_wgs=?,
                                as_cy_wgs=?,
                                as_blx_wgs=?,
                                as_bly_wgs=?,
                                as_tlx_wgs=?,
                                as_tly_wgs=?,
                                as_trx_wgs=?,
                                as_try_wgs=?,
                                as_brx_wgs=?,
                                as_bry_wgs=?
                            WHERE oas_code=?
                            """,
                            (
                                *coord_values,
                                as_code,
                            ),
                        )

                if updates:

                    self.connection.executemany(
                        f"""
                        UPDATE "{table_name}"
                        SET
                            as_cx_wgs=?,
                            as_cy_wgs=?,
                            as_blx_wgs=?,
                            as_bly_wgs=?,
                            as_tlx_wgs=?,
                            as_tly_wgs=?,
                            as_trx_wgs=?,
                            as_try_wgs=?,
                            as_brx_wgs=?,
                            as_bry_wgs=?
                        WHERE oas_code=?
                        """,
                        updates,
                    )

                self.connection.commit()

                print(
                    f"[UPSCALE] "
                    f"Batch completed "
                    f"{min(start + batch_size, total)}"
                    f"/{total}"
                )

    def _checkpoint(self) -> None:

        try:

            result = self.connection.execute(
                "PRAGMA wal_checkpoint(TRUNCATE)"
            ).fetchone()

            busy, log_pages, checkpointed_pages = result

            if busy:

                print(
                    f"[DV] WAL CHECKPOINT: "
                    f"busy=1 — partial. "
                    f"log_pages={log_pages} "
                    f"checkpointed={checkpointed_pages}"
                )

            else:

                print(
                    f"[DV] WAL CHECKPOINT OK — "
                    f"log_pages={log_pages} "
                    f"checkpointed={checkpointed_pages}"
                )

        except Exception as e:

            print(
                f"[DV] WAL CHECKPOINT FAILED: {e}"
            )

    def run(
        self,
        connector_table: str,
        source_size: str,
        as_col_name: str,
    ) -> None:

        oas_codes = (
            self.get_unique_oas_from_connector(
                connector_table,
                source_size,
                as_col_name,
            )
        )

        if not oas_codes:

            print(
                "[UPSCALE] Nothing new to process"
            )

            return

        hierarchy = (
            self.build_hierarchy_upwards(
                oas_codes,
                source_size,
            )
        )

        self.save_hierarchy(
            hierarchy
        )

        self.fill_coordinates()

        print(
            "[UPSCALE] Finished"
        )

        self._checkpoint()

