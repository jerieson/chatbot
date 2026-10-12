# scripts/migrate_json_to_db.py - Create schema and seed intents from JSON
#
# Usage (from project root):
#   python scripts/migrate_json_to_db.py           # create tables, sync intents from JSON
#   python scripts/migrate_json_to_db.py --reset   # also remove intents no longer in the JSON

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.database import Database  # noqa: E402

SCHEMA_PATH = PROJECT_ROOT / "scripts" / "schema.sql"
INTENTS_PATH = PROJECT_ROOT / "chatbot" / "data" / "intents.json"


async def apply_schema():
    statements = [s.strip() for s in SCHEMA_PATH.read_text(encoding="utf-8").split(";")]
    for statement in statements:
        # Skip blank chunks and comment-only chunks
        if any(line.strip() and not line.strip().startswith("--") for line in statement.splitlines()):
            await Database.execute(statement)
    print("Schema applied")


async def reset_intents():
    await Database.execute("DELETE FROM intents")  # cascades to patterns/responses
    print("Existing intents, patterns and responses removed")


async def seed_intents(json_path: Path):
    """Insert new intents and replace patterns/responses of existing ones with the JSON's."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    stats = {"intents": 0, "patterns": 0, "responses": 0, "updated": 0}

    for intent in data.get("intents", []):
        tag = intent["tag"]
        existing = await Database.fetch_one("SELECT id FROM intents WHERE tag = %s", (tag,))
        if existing:
            intent_id = existing["id"]
            await Database.execute(
                "UPDATE intents SET description = %s WHERE id = %s", (intent.get("description", ""), intent_id)
            )
            await Database.execute("DELETE FROM patterns WHERE intent_id = %s", (intent_id,))
            await Database.execute("DELETE FROM responses WHERE intent_id = %s", (intent_id,))
            stats["updated"] += 1
        else:
            cursor = await Database.execute(
                "INSERT INTO intents (tag, description) VALUES (%s, %s)",
                (tag, intent.get("description", "")),
            )
            intent_id = cursor.lastrowid
            stats["intents"] += 1

        for pattern in intent.get("patterns", []):
            await Database.execute(
                "INSERT INTO patterns (intent_id, text) VALUES (%s, %s)", (intent_id, pattern)
            )
            stats["patterns"] += 1

        for response in intent.get("responses", []):
            await Database.execute(
                "INSERT INTO responses (intent_id, text) VALUES (%s, %s)", (intent_id, response)
            )
            stats["responses"] += 1

    print(
        f"Added {stats['intents']} and updated {stats['updated']} intents "
        f"({stats['patterns']} patterns, {stats['responses']} responses)"
    )


async def main(reset: bool):
    await Database.init()
    try:
        await apply_schema()
        if reset:
            await reset_intents()
        await seed_intents(INTENTS_PATH)
    finally:
        await Database.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create schema and seed intents into MySQL")
    parser.add_argument(
        "--reset", action="store_true", help="delete existing intents/patterns/responses first"
    )
    args = parser.parse_args()
    asyncio.run(main(args.reset))
