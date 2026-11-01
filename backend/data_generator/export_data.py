import json
from datetime import datetime
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
import pandas as pd
from openpyxl import load_workbook
from sqlalchemy import CreateTable, inspect, insert, text
from backend.config import EXPORT_DIR, DATA_VERSION, SEED

def _sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _normalize_xlsx(path: Path) -> None:
    """Remove workbook timestamps so seeded exports have stable checksums."""
    workbook = load_workbook(path)
    fixed_time = datetime(2026, 1, 1, 0, 0, 0)
    workbook.properties.created = fixed_time
    workbook.properties.modified = fixed_time
    workbook.save(path)

    temporary_path = path.with_suffix(".normalized.xlsx")
    with ZipFile(path, "r") as source, ZipFile(
        temporary_path, "w", compression=ZIP_DEFLATED, compresslevel=9
    ) as target:
        for name in sorted(source.namelist()):
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = source.getinfo(name).external_attr
            content = source.read(name)
            if name == "docProps/core.xml":
                content = re.sub(
                    rb"(<dcterms:modified[^>]*>)[^<]+(</dcterms:modified>)",
                    rb"\g<1>2026-01-01T00:00:00Z\g<2>",
                    content,
                )
            target.writestr(info, content)
    temporary_path.replace(path)


def export_database(session, dataset_version=DATA_VERSION) -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    (EXPORT_DIR / "csv").mkdir(exist_ok=True)
    (EXPORT_DIR / "json").mkdir(exist_ok=True)
    (EXPORT_DIR / "sql").mkdir(exist_ok=True)
    inspector = inspect(session.bind)
    metadata = session.bind.metadata if hasattr(session.bind, "metadata") else None
    from backend.database.models import Base
    metadata = Base.metadata
    schema_lines = ["-- SQLAlchemy-generated schema and seed export", "BEGIN;"]
    seed_lines = ["-- SQLAlchemy-generated seed data", "BEGIN;"]
    sensitive_tables = {"users"}
    quote = session.bind.dialect.identifier_preparer.quote
    for table in metadata.sorted_tables:
        schema_lines.append(str(CreateTable(table).compile(dialect=session.bind.dialect)) + ";")
        if table.name in sensitive_tables:
            continue
        rows = [dict(row) for row in session.execute(text(f"SELECT * FROM {quote(table.name)}")).mappings()]
        for row in rows:
            columns = ", ".join(quote(name) for name in row)
            values = ", ".join(_sql_literal(value) for value in row.values())
            seed_lines.append(f"INSERT INTO {quote(table.name)} ({columns}) VALUES ({values});")
    schema_lines.append("COMMIT;")
    seed_lines.append("COMMIT;")
    (EXPORT_DIR / "sql" / "schema.sql").write_text("\n".join(schema_lines), encoding="utf-8")
    (EXPORT_DIR / "sql" / "seed_data.sql").write_text("\n".join(seed_lines), encoding="utf-8")
    manifest = []
    for table in sorted(inspector.get_table_names()):
        if table in sensitive_tables:
            continue
        rows = [dict(row) for row in session.execute(text(f"SELECT * FROM {quote(table)}")).mappings()]
        df = pd.DataFrame(rows)
        df.to_csv(EXPORT_DIR / "csv" / f"{table}.csv", index=False)
        (EXPORT_DIR / "json" / f"{table}.json").write_text(json.dumps(rows, default=str, indent=2), encoding="utf-8")
        if table == "anomalies":
            df.to_csv(EXPORT_DIR / "ground_truth.csv", index=False)
            (EXPORT_DIR / "ground_truth.json").write_text(json.dumps(rows, default=str, indent=2), encoding="utf-8")
        manifest.append({"dataset_filename": table, "record_count": len(rows), "generation_method": "seeded synthetic generator",
                         "seed": SEED, "dataset_version": dataset_version, "data_provenance": "Fictional data generated locally",
                         "license": "Synthetic; no external data"})
    (EXPORT_DIR / "source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    dictionary = []
    for table in sorted(inspector.get_table_names()):
        primary_keys = inspector.get_pk_constraint(table)["constrained_columns"]
        for column in inspector.get_columns(table):
            dictionary.append({"entity": table, "column": column["name"], "data_type": str(column["type"]),
                               "required": not column["nullable"], "primary_key": column["name"] in primary_keys})
    dictionary_path = EXPORT_DIR / "data_dictionary.xlsx"
    pd.DataFrame(dictionary).to_excel(dictionary_path, index=False)
    _normalize_xlsx(dictionary_path)
