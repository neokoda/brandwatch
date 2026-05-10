"""
Seed demo accounts + trackers for the recruiting team.
Run: cd backend && python -m scripts.seed

Creates:
  - account: McDonald's  (slug: mcdonalds)
    - user: demo@mcdonalds.com / demo1234
    - trackers: McDonald's Brand, Competitors
  - account: Google  (slug: google)
    - user: demo@google.com / demo1234
    - trackers: Google Cloud, Gemini, Google General
"""
import asyncio
import uuid
from datetime import datetime, timezone
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.database import engine, Base, async_session_factory
from backend.auth import hash_password
from backend.models.account import Account, User
from backend.models.tracker import Tracker


DEMO_DATA = [
    {
        "account": {"name": "McDonald's", "slug": "mcdonalds"},
        "users": [{"email": "demo@mcdonalds.com", "password": "demo1234", "role": "admin"}],
        "trackers": [
            {
                "name": "McDonald's Brand",
                "tracker_type": "brand",
                "keywords": ["McDonald's", "McDonaldsCorp", "McDonalds", "BigMac", "McFlurry"],
                "languages": ["en", "fr", "es"],
                "rss_feeds": [],
            },
            {
                "name": "Competitors",
                "tracker_type": "competitor",
                "keywords": ["Burger King", "Wendy's", "KFC", "Popeyes"],
                "languages": ["en"],
                "rss_feeds": [],
            },
        ],
    },
    {
        "account": {"name": "Google", "slug": "google"},
        "users": [{"email": "demo@google.com", "password": "demo1234", "role": "admin"}],
        "trackers": [
            {
                "name": "Google Cloud",
                "tracker_type": "brand",
                "keywords": ["Google Cloud", "GCP", "Google Cloud Platform", "BigQuery", "Google Kubernetes"],
                "languages": ["en"],
                "rss_feeds": [],
            },
            {
                "name": "Gemini AI",
                "tracker_type": "brand",
                "keywords": ["Gemini AI", "Google Gemini", "Gemini Pro", "Gemini Ultra"],
                "languages": ["en", "fr", "de"],
                "rss_feeds": [],
            },
            {
                "name": "Google General",
                "tracker_type": "brand",
                "keywords": ["Google", "Alphabet", "Sundar Pichai", "Google Search"],
                "languages": ["en"],
                "rss_feeds": [],
            },
        ],
    },
]


async def seed():
    async with async_session_factory() as db:
        for entry in DEMO_DATA:
            acc_data = entry["account"]

            from sqlalchemy import select
            existing = await db.execute(select(Account).where(Account.slug == acc_data["slug"]))
            account = existing.scalar_one_or_none()
            if not account:
                account = Account(
                    id=uuid.uuid4(),
                    name=acc_data["name"],
                    slug=acc_data["slug"],
                    alert_config={},
                )
                db.add(account)
                await db.flush()
                print(f"Created account: {acc_data['name']}")
            else:
                print(f"Account exists: {acc_data['name']}")

            for u_data in entry["users"]:
                existing_u = await db.execute(select(User).where(User.email == u_data["email"]))
                if not existing_u.scalar_one_or_none():
                    user = User(
                        id=uuid.uuid4(),
                        account_id=account.id,
                        email=u_data["email"],
                        password_hash=hash_password(u_data["password"]),
                        role=u_data["role"],
                    )
                    db.add(user)
                    print(f"  Created user: {u_data['email']}")

            for t_data in entry["trackers"]:
                existing_t = await db.execute(
                    select(Tracker).where(Tracker.account_id == account.id, Tracker.name == t_data["name"])
                )
                if not existing_t.scalar_one_or_none():
                    tracker = Tracker(
                        id=uuid.uuid4(),
                        account_id=account.id,
                        name=t_data["name"],
                        tracker_type=t_data["tracker_type"],
                        keywords=t_data["keywords"],
                        languages=t_data.get("languages", []),
                        rss_feeds=t_data.get("rss_feeds", []),
                        is_active=True,
                    )
                    db.add(tracker)
                    print(f"  Created tracker: {t_data['name']}")

        await db.commit()
        print("\nSeed complete.")
        print("\nDemo credentials:")
        print("  McDonald's: demo@mcdonalds.com / demo1234")
        print("  Google:     demo@google.com / demo1234")


if __name__ == "__main__":
    asyncio.run(seed())
