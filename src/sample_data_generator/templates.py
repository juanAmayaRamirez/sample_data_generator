import json
from pathlib import Path

import click
from faker import Faker

TEMPLATES_DIR = Path("templates")
DTYPES = ["string", "int", "float", "date", "bool"]


def _get_faker_methods() -> list[str]:
    fake = Faker()
    methods = set()
    for p in fake.providers:
        for m in dir(p):
            if not m.startswith("_") and callable(getattr(p, m, None)):
                methods.add(m)
    return sorted(methods)


def list_templates() -> list[str]:
    return [f.stem for f in TEMPLATES_DIR.glob("*.json")]


def load_template(name: str) -> dict:
    return json.loads((TEMPLATES_DIR / f"{name}.json").read_text())


def save_template(template: dict) -> None:
    TEMPLATES_DIR.mkdir(exist_ok=True)
    (TEMPLATES_DIR / f"{template['name']}.json").write_text(
        json.dumps(template, indent=2)
    )
    click.echo(f"Template saved to templates/{template['name']}.json")


def create_template() -> dict:
    name = click.prompt("Template/dataset name")
    num_cols = click.prompt("Number of columns", type=int)

    faker_methods = _get_faker_methods()

    columns = []
    for i in range(num_cols):
        click.echo(f"--- Column {i + 1} ---")
        col_name = click.prompt("Column name")
        dtype = click.prompt("Data type", type=click.Choice(DTYPES, case_sensitive=False))
        faker_method = None
        while faker_method not in faker_methods:
            if faker_method is not None:
                click.echo(f"  Invalid method '{faker_method}'. See README.md for full list.")
            faker_method = click.prompt("Faker methods: (name, email, address, phone_number, date, "
               "company, job, city, country, text, random_int, pyfloat, pybool, uuid4)"
               "Full list available in README.md")
        columns.append({"name": col_name, "dtype": dtype, "faker_method": faker_method})
    template = {"name": name, "columns": columns}
    save_template(template)
    return template


def modify_template(name: str) -> dict:
    template = load_template(name)
    faker_methods = _get_faker_methods()

    click.echo(f"\nModifying template '{name}'")
    num_cols = click.prompt("Number of columns", type=int, default=len(template["columns"]))

    columns = []
    for i in range(num_cols):
        old = template["columns"][i] if i < len(template["columns"]) else {}
        click.echo(f"--- Column {i + 1} ---")
        col_name = click.prompt("Column name", default=old.get("name", ""))
        dtype = click.prompt("Data type", type=click.Choice(DTYPES, case_sensitive=False),
                             default=old.get("dtype", "string"))
        faker_method = None
        default_method = old.get("faker_method", "")
        while faker_method not in faker_methods:
            if faker_method is not None:
                click.echo(f"  Invalid method '{faker_method}'. See README.md for full list.")
            faker_method = click.prompt("Faker method", default=default_method)
        columns.append({"name": col_name, "dtype": dtype, "faker_method": faker_method})

    template["columns"] = columns
    save_template(template)
    return template


def pick_or_create_template() -> tuple[dict, str]:
    """Returns (template, dataset_name)."""
    existing = list_templates()
    if existing:
        action = click.prompt(
            "Load, create, or modify a template?",
            type=click.Choice(["load", "create", "modify"], case_sensitive=False),
        )
        if action == "load":
            name = click.prompt("Template", type=click.Choice(existing, case_sensitive=False))
            return load_template(name), name
        if action == "modify":
            name = click.prompt("Template to modify", type=click.Choice(existing, case_sensitive=False))
            return modify_template(name), name
    else:
        click.echo("No templates found — let's create one.")
    template = create_template()
    return template, template["name"]
