"""
Automated Disaster Recovery and Restoration Utility.
Restores PostgreSQL relational records and ChromaDB vector store
from a verified backup archive bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tarfile
from datetime import datetime
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.models import Comment, Post, Subreddit
from backend.repositories.chroma_repository import ChromaRepository




def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def restore_backup(
    backup_path: Path | str,
    target_db_url: str | None = None,
    target_chroma_dir: Path | str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    b_path = Path(backup_path)
    if not b_path.exists():
        raise FileNotFoundError(f"Backup directory not found at {b_path}")

    manifest_file = b_path / "metadata.json"
    if not manifest_file.exists():
        raise ValueError(f"Invalid backup bundle: missing metadata.json in {b_path}")

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"[*] Validating backup manifest (Created: {manifest.get('timestamp_utc')})...")

    # 1. Verify Checksums
    db_file = b_path / "database_export.json"
    if db_file.exists():
        expected_sha = manifest.get("files", {}).get("database_export", {}).get("sha256")
        if expected_sha:
            actual_sha = compute_sha256(db_file)
            if actual_sha != expected_sha:
                raise ValueError(f"Checksum mismatch for {db_file.name}: {actual_sha} != {expected_sha}")
            print(f"[+] Verified checksum for {db_file.name}")

    chroma_tar = b_path / "chromadb.tar.gz"
    if chroma_tar.exists():
        expected_sha = manifest.get("files", {}).get("chromadb_archive", {}).get("sha256")
        if expected_sha:
            actual_sha = compute_sha256(chroma_tar)
            if actual_sha != expected_sha:
                raise ValueError(f"Checksum mismatch for {chroma_tar.name}: {actual_sha} != {expected_sha}")
            print(f"[+] Verified checksum for {chroma_tar.name}")

    if dry_run:
        print("[SUCCESS] [DRY RUN] All backup bundle files and checksums verified successfully!")
        return {"status": "dry_run_success", "manifest": manifest}


    # 2. Restore Relational Database
    db_url = target_db_url or (
        f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )

    restored_counts = {"subreddits": 0, "posts": 0, "comments": 0}

    if db_file.exists():
        with open(db_file, "r", encoding="utf-8") as f:
            export_data = json.load(f)

        engine = create_engine(db_url)
        with Session(engine) as session:
            # Upsert subreddits
            for s_data in export_data.get("subreddits", []):
                existing = session.execute(
                    select(Subreddit).where(Subreddit.name == s_data["name"])
                ).scalar_one_or_none()
                if not existing:
                    sub = Subreddit(
                        id=s_data["id"],
                        name=s_data["name"],
                        url=s_data.get("url"),
                        created_at=datetime.fromisoformat(s_data["created_at"]),
                    )
                    session.add(sub)
                    restored_counts["subreddits"] += 1
            session.commit()

            # Upsert posts
            for p_data in export_data.get("posts", []):
                existing = session.execute(
                    select(Post).where(Post.id == p_data["id"])
                ).scalar_one_or_none()
                if not existing:
                    post = Post(
                        id=p_data["id"],
                        title=p_data["title"],
                        author=p_data.get("author", "[deleted]"),
                        subreddit_id=p_data["subreddit_id"],
                        score=p_data.get("score", 0),
                        comments_count=p_data.get("comments_count", 0),
                        url=p_data["url"],
                        content=p_data.get("content", ""),
                        created_at=datetime.fromisoformat(p_data["created_at"]) if p_data.get("created_at") else None,
                        scraped_at=datetime.fromisoformat(p_data["scraped_at"]) if p_data.get("scraped_at") else None,
                        sentiment_score=p_data.get("sentiment_score"),
                        sentiment_label=p_data.get("sentiment_label"),
                        technologies=p_data.get("technologies"),
                    )
                    session.add(post)
                    restored_counts["posts"] += 1
            session.commit()

            # Upsert comments
            for c_data in export_data.get("comments", []):
                existing = session.execute(
                    select(Comment).where(Comment.id == c_data["id"])
                ).scalar_one_or_none()
                if not existing:
                    comm = Comment(
                        id=c_data["id"],
                        post_id=c_data["post_id"],
                        author=c_data.get("author", "[deleted]"),
                        content=c_data["content"],
                        score=c_data.get("score", 0),
                        created_at=datetime.fromisoformat(c_data["created_at"]) if c_data.get("created_at") else None,
                        sentiment_score=c_data.get("sentiment_score"),
                        sentiment_label=c_data.get("sentiment_label"),
                        technologies=c_data.get("technologies"),
                    )
                    session.add(comm)
                    restored_counts["comments"] += 1
            session.commit()

        print(f"[+] Relational restoration complete. Inserted records: {restored_counts}")

    # 3. Restore ChromaDB Vector Store
    chroma_dest = Path(target_chroma_dir or settings.chroma_persist_directory)
    if chroma_tar.exists():
        chroma_dest.mkdir(parents=True, exist_ok=True)
        with tarfile.open(chroma_tar, "r:gz") as tar:
            tar.extractall(path=chroma_dest.parent)
        print(f"[+] Restored ChromaDB vectors to: {chroma_dest}")

    print("[SUCCESS] Disaster recovery restore completed successfully!")
    return {

        "status": "success",
        "restored_records": restored_counts,
        "backup_timestamp": manifest.get("timestamp_utc"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore Reddit Intelligence Platform from Backup")
    parser.add_argument("backup_path", type=str, help="Path to backup directory")
    parser.add_argument("--dry-run", action="store_true", help="Validate archive integrity without restoring data")
    args = parser.parse_args()

    restore_backup(backup_path=args.backup_path, dry_run=args.dry_run)
