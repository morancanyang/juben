"""Explicit, repeatable schema installation and immutable seed publication."""

from sqlalchemy import select, text

from api.content import checksum, validate_package
from api.db import SessionLocal, engine
from api.models import Base, ScriptVersion
from api.seed_content import make_cases


def migrate():
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(40) PRIMARY KEY)"
            )
        )
        if not conn.execute(
            text("SELECT version FROM schema_migrations WHERE version='001_initial'")
        ).first():
            conn.execute(
                text("INSERT INTO schema_migrations(version) VALUES ('001_initial')")
            )
    with SessionLocal() as db:
        for case in make_cases():
            content, issues = validate_package(case)
            assert content and not [i for i in issues if i["severity"] == "blocker"], (
                issues
            )
            digest = checksum(content)
            existing = db.scalar(
                select(ScriptVersion)
                .where(ScriptVersion.script_id == case["id"])
                .order_by(ScriptVersion.version.desc())
            )
            if existing and existing.checksum == digest:
                continue
            version = existing.version + 1 if existing else 1
            db.add(
                ScriptVersion(
                    id=f"{case['id']}:v{version}",
                    script_id=case["id"],
                    version=version,
                    checksum=digest,
                    content=content,
                )
            )
        db.commit()


if __name__ == "__main__":
    migrate()
    print("Schema 001 and three immutable case versions are ready.")
