from datetime import date, datetime, timedelta

import polars as pl
from faker import Faker

DTYPE_MAP = {
    "string": pl.Utf8,
    "int": pl.Int64,
    "float": pl.Float64,
    "date": pl.Date,
    "bool": pl.Boolean,
}

fake = Faker()


def _generate_value(col: dict, partition_date: date):
    method = col["faker_method"]
    if method == "pybool":
        return str(fake.pybool()).lower()
    if method == "iso8601" and col.get("correlate_partition", False):
        random_time = fake.time_object()
        return datetime.combine(partition_date, random_time).isoformat(timespec="milliseconds")
    return getattr(fake, method)()


def generate(
    template: dict,
    partition_field: str,
    start_date: date,
    end_date: date,
    rows_per_partition: int,
) -> pl.DataFrame:
    dates = []
    d = start_date
    while d <= end_date:
        dates.append(d)
        d += timedelta(days=1)

    all_rows: dict[str, list] = {col["name"]: [] for col in template["columns"]}
    all_rows[partition_field] = []

    for dt in dates:
        for _ in range(rows_per_partition):
            for col in template["columns"]:
                val = _generate_value(col, dt)
                all_rows[col["name"]].append(val)
            all_rows[partition_field].append(str(dt))

    df = pl.DataFrame(all_rows)

    # Cast columns to specified dtypes
    casts = {}
    for col in template["columns"]:
        target = DTYPE_MAP[col["dtype"]]
        if col["dtype"] == "int":
            casts[col["name"]] = pl.col(col["name"]).cast(pl.Utf8).cast(target, strict=False)
        elif col["dtype"] == "float":
            casts[col["name"]] = pl.col(col["name"]).cast(pl.Utf8).cast(target, strict=False)
        elif col["dtype"] == "bool":
            casts[col["name"]] = pl.col(col["name"]).cast(target, strict=False)
        elif col["dtype"] == "date":
            casts[col["name"]] = pl.col(col["name"]).cast(pl.Utf8).str.to_date(strict=False)
        else:
            casts[col["name"]] = pl.col(col["name"]).cast(pl.Utf8)

    if casts:
        df = df.with_columns(**casts)

    return df
