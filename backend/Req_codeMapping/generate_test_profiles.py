#!/usr/bin/env python3
"""
12 Developer Profile Generator for Burnout Detection Testing
SIMPLIFIED version - only inserts essential tables
"""

import os
import sys
import random
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

# Add path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client, Client

# Supabase credentials
SUPABASE_URL = "https://jkwubrrronkyfpmdlvwd.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imprd3VicnJyb25reWZwbWRsdndkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTIwMTgyMCwiZXhwIjoyMDkwNzc3ODIwfQ.C7tkTm7xTYHEd266omj3F1b1FgImqb8wgc3t4DRniIc"

# Configuration
TEAM_ID = "team-alpha"
PROJECT_ID = "deviq-test"
START_DATE = datetime(2026, 3, 1)  # 4 weeks of data

# The 12 distinct developer archetypes
DEVELOPER_PROFILES = [
    {
        "id": "dev-fake",
        "name": "The Fake Hard Worker",
        "email": "fake@deviq.ai",
        "pattern": "gaming",
        "description": "High commit count but low value (lots of tiny commits)",
        "risk_level": "moderate",
        "traits": {
            "commit_frequency": "very_high",
            "commit_quality": "very_low",
            "after_hours_pct": 0.15,
            "weekend_work": False,
            "collaboration": "low",
            "focus_consistency": "low",
            "declining_trend": False,
        }
    },
    {
        "id": "dev-weekend",
        "name": "The Weekend Warrior",
        "email": "weekend@deviq.ai",
        "pattern": "burnout_risk",
        "description": "Works weekends consistently - burnout risk",
        "risk_level": "high",
        "traits": {
            "commit_frequency": "high",
            "commit_quality": "medium",
            "after_hours_pct": 0.30,
            "weekend_work": True,
            "collaboration": "medium",
            "focus_consistency": "medium",
            "declining_trend": False,
        }
    },
    {
        "id": "dev-silent",
        "name": "The Silent Hero",
        "email": "silent@deviq.ai",
        "pattern": "hero",
        "description": "Low commits but massive value when they do commit",
        "risk_level": "low",
        "traits": {
            "commit_frequency": "very_low",
            "commit_quality": "very_high",
            "after_hours_pct": 0.05,
            "weekend_work": False,
            "collaboration": "high",
            "focus_consistency": "high",
            "declining_trend": False,
        }
    },
    {
        "id": "dev-burnout",
        "name": "The Burning Out",
        "email": "burnout@deviq.ai",
        "pattern": "declining",
        "description": "Clear declining trend - from high activity to low",
        "risk_level": "critical",
        "traits": {
            "commit_frequency": "declining",
            "commit_quality": "declining",
            "after_hours_pct": 0.10,
            "weekend_work": False,
            "collaboration": "declining",
            "focus_consistency": "declining",
            "declining_trend": True,
        }
    },
    {
        "id": "dev-team",
        "name": "The Team Player",
        "email": "team@deviq.ai",
        "pattern": "collaborative",
        "description": "High collaboration, reviews PRs, helpful comments",
        "risk_level": "low",
        "traits": {
            "commit_frequency": "medium",
            "commit_quality": "medium",
            "after_hours_pct": 0.10,
            "weekend_work": False,
            "collaboration": "very_high",
            "focus_consistency": "high",
            "declining_trend": False,
        }
    },
    {
        "id": "dev-solo",
        "name": "The Lone Wolf",
        "email": "solo@deviq.ai",
        "pattern": "isolation",
        "description": "Works alone, doesn't collaborate, knowledge silo risk",
        "risk_level": "moderate",
        "traits": {
            "commit_frequency": "medium",
            "commit_quality": "medium",
            "after_hours_pct": 0.20,
            "weekend_work": False,
            "collaboration": "very_low",
            "focus_consistency": "medium",
            "declining_trend": False,
        }
    },
    {
        "id": "dev-junior",
        "name": "The Struggling Junior",
        "email": "junior@deviq.ai",
        "pattern": "struggling",
        "description": "Low productivity, long hours, stressed",
        "risk_level": "high",
        "traits": {
            "commit_frequency": "low",
            "commit_quality": "low",
            "after_hours_pct": 0.40,
            "weekend_work": False,
            "collaboration": "low",
            "focus_consistency": "low",
            "declining_trend": False,
        }
    },
    {
        "id": "dev-maintain",
        "name": "The Maintenance Hero",
        "email": "maintain@deviq.ai",
        "pattern": "maintenance",
        "description": "Fixes bugs, handles incidents, keeps lights on",
        "risk_level": "moderate",
        "traits": {
            "commit_frequency": "medium",
            "commit_quality": "medium",
            "after_hours_pct": 0.25,
            "weekend_work": True,
            "collaboration": "high",
            "focus_consistency": "low",
            "declining_trend": False,
        }
    },
    {
        "id": "dev-feature",
        "name": "The Feature Factory",
        "email": "feature@deviq.ai",
        "pattern": "feature_focus",
        "description": "Ships features fast, skips maintenance/refactoring",
        "risk_level": "low",
        "traits": {
            "commit_frequency": "very_high",
            "commit_quality": "medium",
            "after_hours_pct": 0.20,
            "weekend_work": False,
            "collaboration": "low",
            "focus_consistency": "high",
            "declining_trend": False,
        }
    },
    {
        "id": "dev-night",
        "name": "The Night Owl",
        "email": "night@deviq.ai",
        "pattern": "night_worker",
        "description": "Works late nights consistently",
        "risk_level": "moderate",
        "traits": {
            "commit_frequency": "medium",
            "commit_quality": "medium",
            "after_hours_pct": 0.60,
            "weekend_work": False,
            "collaboration": "low",
            "focus_consistency": "medium",
            "declining_trend": False,
        }
    },
    {
        "id": "dev-balanced",
        "name": "The Perfect Employee",
        "email": "balanced@deviq.ai",
        "pattern": "healthy",
        "description": "Balanced work, consistent output, healthy boundaries",
        "risk_level": "low",
        "traits": {
            "commit_frequency": "medium",
            "commit_quality": "high",
            "after_hours_pct": 0.05,
            "weekend_work": False,
            "collaboration": "high",
            "focus_consistency": "high",
            "declining_trend": False,
        }
    },
    {
        "id": "dev-ghost",
        "name": "The Ghost",
        "email": "ghost@deviq.ai",
        "pattern": "disengaged",
        "description": "Barely any activity, disengaged from work",
        "risk_level": "high",
        "traits": {
            "commit_frequency": "very_low",
            "commit_quality": "low",
            "after_hours_pct": 0.0,
            "weekend_work": False,
            "collaboration": "very_low",
            "focus_consistency": "very_low",
            "declining_trend": True,
        }
    },
]


def generate_daily_activity_record(dev_profile: Dict, date: datetime, week_index: int) -> Dict:
    """Generate a daily activity record matching ACTUAL Supabase schema."""
    
    traits = dev_profile["traits"]
    day_index = date.weekday()
    is_weekend = day_index >= 5
    
    # Determine commit count based on pattern
    freq = traits["commit_frequency"]
    if freq == "very_high":
        base_count = random.randint(15, 25)
    elif freq == "high":
        base_count = random.randint(8, 15)
    elif freq == "medium":
        base_count = random.randint(4, 8)
    elif freq == "low":
        base_count = random.randint(1, 4)
    elif freq == "very_low":
        base_count = random.randint(0, 2)
    elif freq == "declining":
        base_count = int(random.randint(10, 20) * (1.0 - week_index * 0.2))
        if base_count < 1:
            base_count = random.randint(0, 1)
    else:
        base_count = random.randint(2, 5)
    
    # Generate commits data for metrics
    total_commits = 0
    total_lines_added = 0
    total_lines_deleted = 0
    total_files = 0
    commits_after_hours = 0
    
    if not (is_weekend and not traits["weekend_work"]):
        # Work happens on this day
        total_commits = base_count
        
        # Calculate lines based on commit quality
        quality = traits["commit_quality"]
        if quality == "very_high":
            lines_per_commit = random.randint(100, 500)
        elif quality == "high":
            lines_per_commit = random.randint(50, 200)
        elif quality == "medium":
            lines_per_commit = random.randint(20, 100)
        elif quality == "low":
            lines_per_commit = random.randint(5, 30)
        elif quality == "very_low":
            lines_per_commit = random.randint(1, 5)
        elif quality == "declining":
            factor = 1.0 - week_index * 0.2
            lines_per_commit = int(random.randint(50, 200) * factor)
        else:
            lines_per_commit = random.randint(20, 100)
        
        total_lines_added = total_commits * lines_per_commit
        total_lines_deleted = int(total_lines_added * 0.2)
        total_files = max(1, int(total_lines_added / 50))
        
        # After hours commits
        if traits["after_hours_pct"] > 0.3:
            commits_after_hours = int(total_commits * 0.4)
    
    # Weekend work
    commits_weekend = total_commits if is_weekend else 0
    
    # Work hours
    if is_weekend and not traits["weekend_work"]:
        # No work
        active_minutes = 0
        focus_minutes = 0
        is_after_hours = False
        overtime_penalty = 0.0
    else:
        # Calculate work hours
        if traits["after_hours_pct"] > 0.4:  # Night owl
            start_hour = 14
            end_hour = 22 + random.randint(0, 2)
        elif traits["after_hours_pct"] > 0.2:
            start_hour = 9
            end_hour = 18 + random.randint(1, 4)
        else:
            start_hour = 9
            end_hour = 17
        
        # Declining trend
        if traits["declining_trend"]:
            decline_factor = 1.0 - (week_index * 0.15)
            if decline_factor < 0.3:
                decline_factor = 0.3
            end_hour = int(start_hour + (end_hour - start_hour) * decline_factor)
        
        # Weekend hours
        if is_weekend and traits["weekend_work"]:
            start_hour = 10
            end_hour = 15
        
        total_hours = max(0, end_hour - start_hour)
        active_minutes = total_hours * 45
        focus_minutes = int(active_minutes * (0.7 + random.random() * 0.2))
        is_after_hours = end_hour > 19
        
        # Overtime penalty
        overtime_penalty = 0.0
        if is_after_hours:
            overtime_penalty = min(30.0, (end_hour - 19) * 5)
        if is_weekend and traits["weekend_work"]:
            overtime_penalty += 10.0
    
    # Sustainability score
    sustainability_score = max(0.0, 100.0 - overtime_penalty)
    
    # Focus ratio
    focus_ratio = focus_minutes / active_minutes if active_minutes > 0 else 0.0
    
    return {
        "developer_id": dev_profile["id"],
        "team_id": TEAM_ID,
        "activity_date": date.strftime("%Y-%m-%d"),
        "commits": total_commits,
        "commits_after_hours": commits_after_hours,
        "commits_weekend": commits_weekend,
        "lines_added": total_lines_added,
        "lines_removed": total_lines_deleted,
        "files_modified": total_files,
        "active_minutes": int(active_minutes),
        "focus_minutes": int(focus_minutes),
        "focus_ratio": round(min(1.0, focus_ratio), 2),
        "is_after_hours": is_after_hours,
        "is_weekend": is_weekend,
        "context_switches": random.randint(1, 10) if active_minutes > 0 else 0,
        "interruption_count": random.randint(0, 5) if active_minutes > 0 else 0,
        "debug_sessions": random.randint(0, 3) if active_minutes > 0 else 0,
        "meeting_minutes": random.randint(0, 60) if active_minutes > 0 else 0,
        "idle_minutes": random.randint(30, 120) if active_minutes > 0 else 0,
        "sustainability_score": round(sustainability_score, 2),
        "overtime_penalty": round(overtime_penalty, 2),
    }


def generate_test_requirements() -> List[Dict]:
    """Generate 5 test requirements with different assignments."""
    
    return [
        {
            "req_id": "REQ-001",
            "title": "User Authentication System",
            "description": "Implement OAuth2-based user authentication with support for Google and GitHub providers. Must include JWT token management and refresh token rotation.",
            "status": "in_progress",
            "assigned_to": "dev-balanced",
            "priority": "high",
            "story_points": 13,
            "created_date": (START_DATE - timedelta(days=14)).strftime("%Y-%m-%d"),
            "target_date": (START_DATE + timedelta(days=14)).strftime("%Y-%m-%d"),
        },
        {
            "req_id": "REQ-002",
            "title": "Database Migration Tool",
            "description": "Create a database migration system with rollback support. Must handle schema versioning and data transformations safely.",
            "status": "in_progress",
            "assigned_to": "dev-burnout",
            "priority": "high",
            "story_points": 21,
            "created_date": (START_DATE - timedelta(days=21)).strftime("%Y-%m-%d"),
            "target_date": (START_DATE + timedelta(days=7)).strftime("%Y-%m-%d"),
        },
        {
            "req_id": "REQ-003",
            "title": "API Rate Limiting",
            "description": "Implement Redis-based rate limiting for all public APIs. Should support tiered limits per API key.",
            "status": "in_progress",
            "assigned_to": "dev-silent",
            "priority": "medium",
            "story_points": 8,
            "created_date": (START_DATE - timedelta(days=10)).strftime("%Y-%m-%d"),
            "target_date": (START_DATE + timedelta(days=10)).strftime("%Y-%m-%d"),
        },
        {
            "req_id": "REQ-004",
            "title": "Real-time Notifications",
            "description": "Build WebSocket-based notification system for real-time alerts. Must support 10k concurrent connections.",
            "status": "in_progress",
            "assigned_to": "dev-feature",
            "priority": "medium",
            "story_points": 13,
            "created_date": (START_DATE - timedelta(days=7)).strftime("%Y-%m-%d"),
            "target_date": (START_DATE + timedelta(days=7)).strftime("%Y-%m-%d"),
        },
        {
            "req_id": "REQ-005",
            "title": "Analytics Dashboard",
            "description": "Create analytics dashboard with custom report builder. Should export to PDF and CSV formats.",
            "status": "in_progress",
            "assigned_to": "dev-ghost",
            "priority": "low",
            "story_points": 21,
            "created_date": (START_DATE - timedelta(days=28)).strftime("%Y-%m-%d"),
            "target_date": START_DATE.strftime("%Y-%m-%d"),
        },
    ]


async def insert_data_to_supabase(supabase: Client, dev_profiles: List[Dict]):
    """Insert all generated data into Supabase tables."""
    
    print("\n=== Inserting Developer Data to Supabase ===\n")
    
    # Generate 4 weeks of data
    developer_activity = []
    
    for week in range(4):
        week_start = START_DATE + timedelta(weeks=week)
        print(f"Generating Week {week + 1} ({week_start.strftime('%Y-%m-%d')})...")
        
        for day in range(7):
            date = week_start + timedelta(days=day)
            
            for dev in dev_profiles:
                activity = generate_daily_activity_record(dev, date, week)
                developer_activity.append(activity)
    
    print(f"\nGenerated {len(developer_activity)} daily activity records")
    
    # Insert developer activity in batches
    print("\nInserting developer activity...")
    batch_size = 100
    inserted_activity = 0
    for i in range(0, len(developer_activity), batch_size):
        batch = developer_activity[i:i+batch_size]
        try:
            result = supabase.table("developer_activity").insert(batch).execute()
            inserted_activity += len(batch)
            print(f"  Batch {i//batch_size + 1}: {len(batch)} records inserted")
        except Exception as e:
            print(f"  Batch {i//batch_size + 1} failed: {str(e)[:100]}")
    
    # Insert test requirements (skip if already exist)
    print("\nInserting test requirements...")
    requirements = generate_test_requirements()
    inserted_reqs = 0
    try:
        # Try to update existing instead of insert
        for req in requirements:
            try:
                result = supabase.table("requirements").insert(req).execute()
                inserted_reqs += 1
            except Exception as e:
                if "duplicate" in str(e).lower():
                    # Update existing
                    result = supabase.table("requirements").update({
                        "assigned_to": req["assigned_to"],
                        "status": req["status"]
                    }).eq("req_id", req["req_id"]).execute()
                    inserted_reqs += 1
        print(f"  {inserted_reqs} requirements inserted/updated")
    except Exception as e:
        print(f"  Requirements insert failed: {str(e)[:100]}")
    
    print("\n=== Data Insertion Complete ===\n")
    
    print(f"\nSUMMARY:")
    print(f"  Activity records inserted: {inserted_activity}/{len(developer_activity)}")
    print(f"  Requirements inserted/updated: {inserted_reqs}/{len(requirements)}")
    
    print("\n=== DEVELOPER PROFILE SUMMARY ===")
    print("-" * 80)
    for dev in dev_profiles:
        print(f"\n{dev['name']} ({dev['id']})")
        print(f"  Pattern: {dev['pattern']}")
        print(f"  Expected Risk: {dev['risk_level'].upper()}")
        print(f"  {dev['description']}")
    print("-" * 80)
    
    print("\n=== TEST REQUIREMENTS ===")
    for req in requirements:
        print(f"\n{req['req_id']}: {req['title']}")
        print(f"  Assigned to: {req['assigned_to']}")
        print(f"  Story Points: {req['story_points']}")
    print("-" * 80)


async def main():
    """Main entry point."""
    
    print("=" * 80)
    print("12 DEVELOPER PROFILE GENERATOR (Simplified)")
    print("=" * 80)
    print("\nThis script inserts only essential tables:")
    print("- developer_activity (for burnout detection)")
    print("- requirements (for delivery prediction)")
    
    # Initialize Supabase client
    print("\nConnecting to Supabase...")
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # Check connection
    try:
        result = supabase.table("developer_activity").select("count", count="exact").limit(1).execute()
        print("[OK] Connected to Supabase")
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return
    
    # Ask for confirmation
    print("\n" + "!" * 80)
    print("WARNING: This will insert synthetic data into your Supabase tables.")
    print("Existing data will NOT be deleted, but duplicate entries may occur.")
    print("!" * 80)
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        response = "yes"
        print("\nAuto-proceeding with --force flag...")
    else:
        response = input("\nProceed with data generation? (yes/no): ").strip().lower()
    
    if response == "yes":
        await insert_data_to_supabase(supabase, DEVELOPER_PROFILES)
        
        print("\n" + "=" * 80)
        print("NEXT STEPS:")
        print("=" * 80)
        print("\n1. Test the dashboard at: https://dev-iq-iota.vercel.app")
        print("   - Go to 'Health & Predictions' tab")
        print("\n2. Test APIs:")
        print("   curl https://deviq-gk7z.onrender.com/api/teams/team-alpha/burnout-summary")
        print("   curl https://deviq-gk7z.onrender.com/api/requirements/REQ-002/delivery-prediction")
        print("\n" + "=" * 80)
    else:
        print("\nCancelled. No data was inserted.")


if __name__ == "__main__":
    asyncio.run(main())
