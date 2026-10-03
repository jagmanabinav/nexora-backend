#!/usr/bin/env python3
"""
Database initialization script.

Usage:
    python scripts/init_db.py
"""

import sys
import asyncio
from pathlib import Path

# Add the parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import engine
from app.models.base import Base


def init_db():
    """Initialize database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database initialization complete!")


if __name__ == "__main__":
    init_db()
