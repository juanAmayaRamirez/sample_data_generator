from pathlib import Path

import polars as pl


def write_partitioned(
    df: pl.DataFrame,
    base_path: Path,
    partition_field: str,
    fmt: str,
) -> None:
    base_path.mkdir(parents=True, exist_ok=True)

    if fmt == "parquet":
        df.write_parquet(str(base_path), partition_by=[partition_field])
    else:
        ext = "csv" if fmt == "csv" else "json"
        for value, group in df.group_by(partition_field):
            part_dir = base_path / f"{partition_field}={value[0]}"
            part_dir.mkdir(parents=True, exist_ok=True)
            data = group.drop(partition_field)
            if fmt == "csv":
                data.write_csv(part_dir / f"data.{ext}")
            else:
                data.write_json(part_dir / f"data.{ext}")
