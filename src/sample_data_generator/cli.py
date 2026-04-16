import signal
import sys
from datetime import datetime
from pathlib import Path

import click

from sample_data_generator.generator import generate
from sample_data_generator.templates import pick_or_create_template
from sample_data_generator.writer import write_partitioned

FORMATS = ["parquet", "csv", "json"]

signal.signal(signal.SIGINT, lambda *_: sys.exit(1))


@click.command()
def main():
    """Interactive sample data generator."""
    template, dataset_name = pick_or_create_template()

    fmt = click.prompt("\nOutput format", type=click.Choice(FORMATS, case_sensitive=False))
    partition_field = click.prompt("Partition field name", default="dt")
    start_date = click.prompt("Start date (YYYY-MM-DD)", type=click.DateTime(["%Y-%m-%d"])).date()
    end_date = click.prompt("End date (YYYY-MM-DD)", type=click.DateTime(["%Y-%m-%d"])).date()
    rows_per_partition = click.prompt("Rows per partition", type=int)

    click.echo("\nGenerating data...")
    df = generate(template, partition_field, start_date, end_date, rows_per_partition)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_path = Path("output") / f"{timestamp}_{dataset_name}"

    click.echo(f"Writing to {base_path}/...")
    write_partitioned(df, base_path, partition_field, fmt)

    num_partitions = df[partition_field].n_unique()
    click.echo(f"\nDone! {len(df)} total rows across {num_partitions} partitions → {base_path}/")

    if click.confirm("\nUpload to S3?", default=False):
        s3_prefix = click.prompt("S3 destination (e.g. s3://bucket/path/)")
        upload_to_s3(base_path, s3_prefix)


def upload_to_s3(local_path: Path, s3_prefix: str) -> None:
    import boto3

    s3_prefix = s3_prefix.rstrip("/")
    bucket, _, prefix = s3_prefix.removeprefix("s3://").partition("/")
    s3 = boto3.client("s3")

    files = [f for f in local_path.rglob("*") if f.is_file()]
    for f in files:
        rel = f.relative_to(local_path).as_posix()
        key = f"{prefix}/{rel}" if prefix else rel
        click.echo(f"  Uploading {f.relative_to(local_path)} → s3://{bucket}/{key}")
        s3.upload_file(str(f), bucket, key)
    click.echo(f"Uploaded {len(files)} files to s3://{bucket}/{prefix}/")
