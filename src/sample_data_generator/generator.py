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

_unicode_counter = 0


def _next_unicode_char() -> str:
    global _unicode_counter
    # Skip surrogates (U+D800–U+DFFF)
    while 0xD800 <= _unicode_counter <= 0xDFFF:
        _unicode_counter += 1
    if _unicode_counter > 0x10FFFF:
        _unicode_counter = 0
    ch = chr(_unicode_counter)
    _unicode_counter += 1
    return ch


def _generate_value(col: dict, partition_date: date):
    method = col["faker_method"]
    if method == "unicode_char":
        return _next_unicode_char()
    if method == "pybool":
        return str(fake.pybool()).lower()
    if method == "iso8601" and col.get("correlate_partition", False):
        random_time = fake.time_object()
        return datetime.combine(partition_date, random_time).isoformat(timespec="milliseconds")
    value = getattr(fake, method)()
    max_length = col.get("max_length")
    if max_length and isinstance(value, str):
        value = value[:max_length]
    return value


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
