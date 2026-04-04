#!/usr/bin/env python3
"""
Generate Synthetic Delivery Pipeline Data (PR, CI, Deployment)
Populates extension_events with PR, CI, and deployment stages
"""

import os
import sys
import random
import asyncio
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client, Client

SUPABASE_URL = "https://jkwubrrronkyfpmdlvwd.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imprd3VicnJyb25reWZwbWRsdndkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTIwMTgyMCwiZXhwIjoyMDkwNzc3ODIwfQ.C7tkTm7xTYHEd266omj3F1b1FgImqb8wgc3t4DRniIc"

REPO_NAME = "deviq-platform"

# The 12 developers
DEVELOPERS = [
    {"id": "dev-fake", "name": "Alex Johnson", "email": "alex@deviq.ai"},
    {"id": "dev-weekend", "name": "Sarah Chen", "email": "sarah@deviq.ai"},
    {"id": "dev-silent", "name": "Mike Ross", "email": "mike@deviq.ai"},
    {"id": "dev-burnout", "name": "Emily Davis", "email": "emily@deviq.ai"},
    {"id": "dev-team", "name": "Chris Lee", "email": "chris@deviq.ai"},
    {"id": "dev-solo", "name": "Jordan Taylor", "email": "jordan@deviq.ai"},
    {"id": "dev-junior", "name": "Sam Wilson", "email": "sam@deviq.ai"},
    {"id": "dev-maintain", "name": "Pat Brown", "email": "pat@deviq.ai"},
    {"id": "dev-feature", "name": "Casey White", "email": "casey@deviq.ai"},
    {"id": "dev-night", "name": "Riley Green", "email": "riley@deviq.ai"},
    {"id": "dev-balanced", "name": "Morgan Black", "email": "morgan@deviq.ai"},
    {"id": "dev-ghost", "name": "Drew Gray", "email": "drew@deviq.ai"},
]


def generate_pr_events(commit_id: str, issue_id: str, developer: dict, base_time: datetime) -> list:
    """Generate PR events for a commit (simplified for existing schema)"""
    import uuid
    pr_number = random.randint(100, 999)
    
    return [
        {
            "commit_id": str(uuid.uuid4()),
            "event_type": "pr_created",
            "timestamp": base_time.isoformat(),
            "pull_request_number": pr_number,
            "pr_title": f"{issue_id}: Implementation",
            "repository_name": REPO_NAME,
            "developer_id": developer["id"],
            "author": developer["name"],
            "author_email": developer["email"],
            "issue_id": issue_id,
            "linked_issue": issue_id,
            "message": f"PR created for {issue_id}",
            "additions": random.randint(10, 200),
            "deletions": random.randint(0, 50),
            "total_changes": 0,
            "active_minutes": random.randint(30, 120),
            "attendance_pct": random.randint(85, 100),
            "focus_ratio": round(random.uniform(0.7, 0.95), 2),
            "created_at": base_time.isoformat(),
            "is_merge_commit": False,
        },
        {
            "commit_id": str(uuid.uuid4()),
            "event_type": "pr_merged",
            "timestamp": (base_time + timedelta(hours=random.randint(2, 48))).isoformat(),
            "pull_request_number": pr_number,
            "pr_title": f"{issue_id}: Implementation",
            "repository_name": REPO_NAME,
            "developer_id": developer["id"],
            "author": developer["name"],
            "author_email": developer["email"],
            "issue_id": issue_id,
            "linked_issue": issue_id,
            "message": f"PR merged for {issue_id}",
            "additions": 0,
            "deletions": 0,
            "total_changes": 0,
            "active_minutes": 0,
            "attendance_pct": 100,
            "focus_ratio": 0.0,
            "created_at": (base_time + timedelta(hours=random.randint(2, 48))).isoformat(),
            "is_merge_commit": True,
        }
    ]


def generate_ci_events(commit_id: str, issue_id: str, developer: dict, base_time: datetime) -> list:
    """Generate CI events for a commit (simplified for existing schema)"""
    import uuid
    return [
        {
            "commit_id": str(uuid.uuid4()),
            "event_type": "ci_build",
            "timestamp": (base_time + timedelta(minutes=random.randint(1, 10))).isoformat(),
            "repository_name": REPO_NAME,
            "developer_id": developer["id"],
            "author": developer["name"],
            "author_email": developer["email"],
            "issue_id": issue_id,
            "linked_issue": issue_id,
            "message": f"CI build for {issue_id}",
            "additions": 0,
            "deletions": 0,
            "total_changes": 0,
            "active_minutes": random.randint(5, 20),
            "attendance_pct": 100,
            "focus_ratio": 0.5,
            "created_at": (base_time + timedelta(minutes=random.randint(1, 10))).isoformat(),
            "is_merge_commit": False,
        }
    ]


def generate_deployment_events(commit_id: str, issue_id: str, developer: dict, base_time: datetime) -> list:
    """Generate deployment events for a commit (simplified for existing schema)"""
    import uuid
    return [
        {
            "commit_id": str(uuid.uuid4()),
            "event_type": "deployment",
            "timestamp": (base_time + timedelta(minutes=random.randint(30, 60))).isoformat(),
            "repository_name": REPO_NAME,
            "developer_id": developer["id"],
            "author": developer["name"],
            "author_email": developer["email"],
            "issue_id": issue_id,
            "linked_issue": issue_id,
            "message": f"Deployed {issue_id} to production",
            "additions": 0,
            "deletions": 0,
            "total_changes": 0,
            "active_minutes": 0,
            "attendance_pct": 100,
            "focus_ratio": 0.0,
            "created_at": (base_time + timedelta(minutes=random.randint(30, 60))).isoformat(),
            "is_merge_commit": False,
        }
    ]


def generate_ci_events(commit_id: str, issue_id: str, developer: dict, base_time: datetime) -> list:
    """Generate CI events for a commit (simplified for existing schema)"""
    return [
        {
            "commit_id": commit_id,
            "event_type": "ci_build",
            "timestamp": (base_time + timedelta(minutes=random.randint(1, 10))).isoformat(),
            "repository_name": REPO_NAME,
            "developer_id": developer["id"],
            "author": developer["name"],
            "author_email": developer["email"],
            "issue_id": issue_id,
            "linked_issue": issue_id,
            "message": f"CI build for {issue_id}",
            "additions": 0,
            "deletions": 0,
            "total_changes": 0,
            "active_minutes": random.randint(5, 20),
            "created_at": (base_time + timedelta(minutes=random.randint(1, 10))).isoformat(),
            "is_merge_commit": False,
        }
    ]


def generate_deployment_events(commit_id: str, issue_id: str, developer: dict, base_time: datetime) -> list:
    """Generate deployment events for a commit (simplified for existing schema)"""
    return [
        {
            "commit_id": commit_id,
            "event_type": "deployment",
            "timestamp": (base_time + timedelta(minutes=random.randint(30, 60))).isoformat(),
            "repository_name": REPO_NAME,
            "developer_id": developer["id"],
            "author": developer["name"],
            "author_email": developer["email"],
            "issue_id": issue_id,
            "linked_issue": issue_id,
            "message": f"Deployed {issue_id} to production",
            "additions": 0,
            "deletions": 0,
            "total_changes": 0,
            "active_minutes": 0,
            "created_at": (base_time + timedelta(minutes=random.randint(30, 60))).isoformat(),
            "is_merge_commit": False,
        }
    ]


async def generate_delivery_pipeline_data(supabase: Client):
    """Generate PR, CI, and deployment events for existing commits"""
    
    print("=" * 80)
    print("GENERATING DELIVERY PIPELINE DATA")
    print("=" * 80)
    
    # Fetch existing commits
    print("\n1. Fetching existing commits...")
    commits_result = supabase.table("extension_events").select("commit_id, issue_id, developer_id, timestamp, author, author_email").eq("event_type", "commit").execute()
    
    if not commits_result.data:
        print("   No commits found! Run generate_jira_github_data.py first.")
        return
    
    commits = commits_result.data
    print(f"   Found {len(commits)} commits")
    
    # Generate pipeline events
    print("\n2. Generating PR/CI/Deployment events...")
    all_events = []
    
    for idx, commit in enumerate(commits):
        commit_id = commit.get("commit_id")
        issue_id = commit.get("issue_id")
        dev_id = commit.get("developer_id")
        timestamp_str = commit.get("timestamp")
        
        if not commit_id or not issue_id:
            continue
        
        # Parse timestamp
        try:
            base_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            base_time = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
        
        # Find developer
        developer = next((d for d in DEVELOPERS if d["id"] == dev_id), DEVELOPERS[0])
        
        # Generate pipeline events with unique timestamps (add milliseconds offset)
        if random.random() < 0.7:  # 70% have PRs
            pr_events = generate_pr_events(commit_id, issue_id, developer, base_time + timedelta(milliseconds=idx))
            for evt in pr_events:
                evt['timestamp'] = (base_time + timedelta(milliseconds=idx, seconds=random.randint(1, 60))).isoformat()
                all_events.append(evt)
        
        if random.random() < 0.6:  # 60% have CI
            ci_events = generate_ci_events(commit_id, issue_id, developer, base_time + timedelta(milliseconds=idx))
            for evt in ci_events:
                evt['timestamp'] = (base_time + timedelta(milliseconds=idx, seconds=random.randint(61, 120))).isoformat()
                all_events.append(evt)
        
        if random.random() < 0.4:  # 40% have deployments
            deploy_events = generate_deployment_events(commit_id, issue_id, developer, base_time + timedelta(milliseconds=idx))
            for evt in deploy_events:
                evt['timestamp'] = (base_time + timedelta(milliseconds=idx, seconds=random.randint(121, 180))).isoformat()
                all_events.append(evt)
    
    print(f"   Generated {len(all_events)} pipeline events")
    
    # Insert events individually to handle duplicates
    print("\n3. Inserting pipeline events...")
    inserted = 0
    duplicates = 0
    errors = 0
    
    for i, event in enumerate(all_events):
        try:
            result = supabase.table("extension_events").insert(event).execute()
            inserted += 1
            if i % 50 == 0:
                print(f"   Progress: {i}/{len(all_events)} (inserted: {inserted}, dupes: {duplicates}, errors: {errors})")
        except Exception as e:
            if "duplicate" in str(e).lower():
                duplicates += 1
            else:
                errors += 1
                if errors < 5:  # Only print first few errors
                    print(f"   Error: {str(e)[:60]}")
    
    # Calculate metrics
    pr_count = sum(1 for e in all_events if "pr_" in e.get("event_type", ""))
    ci_count = sum(1 for e in all_events if "ci_" in e.get("event_type", ""))
    deploy_count = sum(1 for e in all_events if e.get("event_type") == "deployment")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal pipeline events generated: {len(all_events)}")
    print(f"  Inserted: {inserted}")
    print(f"  Duplicates skipped: {duplicates}")
    print(f"  Errors: {errors}")
    print(f"\n  PR events: {pr_count}")
    print(f"  CI events: {ci_count}")
    print(f"  Deployment events: {deploy_count}")
    
    print("\nDELIVERY TIMELINE SHOULD NOW SHOW:")
    print(f"  - Requirements with PRs: ~{pr_count // 2}")
    print(f"  - Requirements with CI: ~{ci_count}")
    print(f"  - Requirements deployed: ~{deploy_count}")
    
    print("\n" + "=" * 80)
    print("NEXT: Refresh dashboard at https://dev-iq-iota.vercel.app")
    print("The Delivery Timeline section should now show real numbers!")
    print("=" * 80)


async def main():
    print("=" * 80)
    print("DELIVERY PIPELINE DATA GENERATOR")
    print("=" * 80)
    print("\nThis adds PR, CI, and deployment events to extension_events")
    print("so the Delivery Timeline section shows complete pipeline data.")
    
    print("\nConnecting to Supabase...")
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    try:
        result = supabase.table("extension_events").select("count", count="exact").limit(1).execute()
        print("[OK] Connected")
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return
    
    print("\n" + "!" * 80)
    print("This will add synthetic PR, CI, and deployment events.")
    print("Run this AFTER generate_jira_github_data.py")
    print("!" * 80)
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        response = "yes"
        print("\nAuto-proceeding with --force...")
    else:
        response = input("\nProceed? (yes/no): ").strip().lower()
    
    if response == "yes":
        await generate_delivery_pipeline_data(supabase)
    else:
        print("\nCancelled.")


if __name__ == "__main__":
    asyncio.run(main())
