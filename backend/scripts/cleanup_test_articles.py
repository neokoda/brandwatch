"""
Delete test/placeholder mentions from the database.
These are mentions with content like "Test article N about X" that were inserted
during development or early seeding.

Run: cd backend && python -m scripts.cleanup_test_articles
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import delete, select, func
from backend.database import async_session_factory
from backend.models.mention import Mention


async def main():
    async with async_session_factory() as db:
        # Count first
        count_result = await db.execute(
            select(func.count()).where(Mention.content_text.ilike("Test article%"))
        )
        count = count_result.scalar_one()
        print(f"Found {count} test article mentions to delete")

        if count == 0:
            print("Nothing to delete.")
            return

        await db.execute(
            delete(Mention).where(Mention.content_text.ilike("Test article%"))
        )
        await db.commit()
        print(f"Deleted {count} test article mentions.")
        print("Run topics recluster via the UI (Topics page > Recluster) to refresh clusters.")


if __name__ == "__main__":
    asyncio.run(main())
