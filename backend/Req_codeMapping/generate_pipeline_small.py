#!/usr/bin/env python3
"""
Memory-Efficient Delivery Pipeline Data Generator
Uses small batches to avoid memory issues
"""

import os
import sys
import random
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client, Client

SUPABASE_URL = "https://jkwubrrronkyfpmdlvwd.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imprd3VicnJyb25reWZwbWRsdndkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTIwMTgyMCwiZXhwIjoyMDkwNzc3ODIwfQ.C7tkTm7xTYHEd266omj3F1b1FgImqb8wgc3t4DRniIc"

REPO_NAME = "deviq-platform"

DEVELOPERS = [
    {"id": "dev-fake", "name": "Alex Johnson"},
    {"id": "dev-weekend", "name": "Sarah Chen"},
    {"id": "dev-silent", "name": "Mike Ross"},
    {"id": "dev-burnout", "name": "Emily Davis"},
    {"id": "dev-team", "name": "Chris Lee"},
    {"id": "dev-solo", "name": "Jordan Taylor"},
    {"id": "dev-junior", "name": "Sam Wilson"},
    {"id": "dev-maintain", "name": "Pat Brown"},
    {"id": "dev-feature", "name": "Casey White"},
    {"id": "dev-night", "name": "Riley Green"},
    {"id": "dev-balanced", "name": "Morgan Black"},
    {"id": "dev-ghost", "name": "Drew Gray"},
]


def generate_pipeline_event(commit_id: str, issue_id: str, dev_id: str, event_type: str, base_time: datetime) -> dict:
    """Generate a single pipeline event with minimal fields"""
    developer = next((d for d in DEVELOPERS if d["id"] == dev_id), DEVELOPERS[0])
    
    event = {
        "commit_id": str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": base_time.isoformat(),
        "repository_name": REPO_NAME,
        "developer_id": dev_id,
        "author": developer["name"],
        "issue_id": issue_id,
        "linked_issue": issue_id,
        "message": f"{event_type} for {issue_id}",
        "additions": 0,
        "deletions": 0,
        "total_changes": 0,
        "active_minutes": 0,
        "attendance_pct": 100,
        "focus_ratio": 0.0,
        "created_at": base_time.isoformat(),
        "is_merge_commit": False,
    }
    
    if "pr" in event_type:
        event["pull_request_number"] = random.randint(100, 999)
        event["pr_title"] = f"{issue_id}: Implementation"
        event["active_minutes"] = random.randint(30, 120)
        event["focus_ratio"] = round(random.uniform(0.7, 0.95), 2)
        if "pr_created" in event_type:
            event["additions"] = random.randint(10, 200)
            event["deletions"] = random.randint(0, 50)
    
    return event


async def insert_in_batches(supabase: Client, events: list, batch_size: int = 10):
    """Insert events in small batches with delays"""
    inserted = 0
    duplicates = 0
    
    for i in range(0, len(events), batch_size):
        batch = events[i:i+batch_size]
        try:
            result = supabase.table("extension_events").insert(batch).execute()
            inserted += len(batch)
        except Exception as e:
            if "duplicate" in str(e).lower():
                duplicates += len(batch)
            else:
                print(f"Batch error: {str(e)[:50]}")
        
        # Small delay to prevent overwhelming the API
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(events)} inserted")
            await asyncio.sleep(0.1)
    
    return inserted, duplicates


async def main():
    print("=" * 60)
    print("MEMORY-EFFICIENT PIPELINE DATA GENERATOR")
    print("=" * 60)
    
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("Connected to Supabase\n")
    
    # Fetch commits in small batches
    print("1. Fetching commits...")
    result = supabase.table("extension_events").select(
        "commit_id, issue_id, developer_id, timestamp"
    ).eq("event_type", "commit").limit(100).execute()
    
    if not result.data:
        print("No commits found!")
        return
    
    commits = result.data
    print(f"Found {len(commits)} commits\n")
    
    # Generate events
    print("2. Generating pipeline events...")
    events = []
    
    for idx, commit in enumerate(commits):
        commit_id = commit.get("commit_id")
        issue_id = commit.get("issue_id")
        dev_id = commit.get("developer_id")
        timestamp_str = commit.get("timestamp")
        
        if not all([commit_id, issue_id, dev_id]):
            continue
        
        try:
            base_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            base_time = datetime.now(timezone.utc)
        
        # Add some variation to timestamps
        time_offset = timedelta(minutes=idx)
        
        # PR events (70% of commits)
        if random.random() < 0.7:
            events.append(generate_pipeline_event(commit_id, issue_id, dev_id, "pr_created", base_time + time_offset))
            events.append(generate_pipeline_event(commit_id, issue_id, dev_id, "pr_merged", base_time + time_offset + timedelta(hours=2)))
        
        # CI events (60%)
        if random.random() < 0.6:
            events.append(generate_pipeline_event(commit_id, issue_id, dev_id, "ci_build", base_time + time_offset + timedelta(minutes=5)))
        
        # Deployment events (40%)
        if random.random() < 0.4:
            events.append(generate_pipeline_event(commit_id, issue_id, dev_id, "deployment", base_time + time_offset + timedelta(minutes=30)))
    
    print(f"Generated {len(events)} events\n")
    
    # Insert in small batches
    print("3. Inserting in small batches...")
    inserted, duplicates = await insert_in_batches(supabase, events, batch_size=10)
    
    print(f"\n{'='*60}")
    print(f"Inserted: {inserted}")
    print(f"Duplicates: {duplicates}")
    print(f"\nDashboard should now show pipeline data!")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
