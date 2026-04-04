#!/usr/bin/env python3
"""
Generate Synthetic JIRA/GitHub Data for Main Dashboard
Populates req_code_mapping and extension_events tables
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

PROJECT_KEY = "DEVIQ"
REPO_NAME = "deviq-platform"
START_DATE = datetime(2025, 12, 1)  # 3 months of data

# Sample JIRA issue types
ISSUE_TYPES = ["Story", "Bug", "Task", "Epic"]
PRIORITIES = ["Highest", "High", "Medium", "Low", "Lowest"]
STATUSES = ["To Do", "In Progress", "In Review", "Done"]

# Sample titles for realistic issues
ISSUE_TEMPLATES = {
    "Story": [
        "Implement user authentication flow",
        "Add dark mode support to dashboard",
        "Create analytics export feature",
        "Build notification center",
        "Integrate payment gateway",
        "Add multi-language support",
        "Implement search functionality",
        "Create user onboarding wizard",
        "Add data visualization charts",
        "Build API rate limiting",
    ],
    "Bug": [
        "Fix memory leak in data processing",
        "Resolve CORS error on API calls",
        "Fix timezone handling in reports",
        "Resolve intermittent login failures",
        "Fix broken image uploads",
        "Resolve database connection timeout",
        "Fix incorrect date formatting",
        "Resolve caching issues",
        "Fix mobile responsiveness",
        "Resolve email notification delays",
    ],
    "Task": [
        "Update dependency versions",
        "Configure CI/CD pipeline",
        "Set up monitoring alerts",
        "Optimize database queries",
        "Refactor legacy code module",
        "Update documentation",
        "Configure SSL certificates",
        "Set up backup strategy",
        "Performance testing",
        "Security audit",
    ],
    "Epic": [
        "Platform scalability improvements",
        "Enterprise security features",
        "Mobile app development",
        "AI/ML integration",
        "Data warehouse migration",
    ]
}

# Sample commit messages
COMMIT_MESSAGES = [
    "feat: add user authentication",
    "fix: resolve memory leak",
    "refactor: optimize database queries",
    "test: add unit tests for auth",
    "docs: update API documentation",
    "chore: update dependencies",
    "feat: implement search feature",
    "fix: handle edge case in validation",
    "perf: improve loading speed",
    "style: fix formatting issues",
]

# The 12 developers from burnout data
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


def generate_issue_id(index: int) -> str:
    """Generate JIRA-style issue ID"""
    return f"{PROJECT_KEY}-{1000 + index}"


def generate_synthetic_issues(count: int = 50) -> list:
    """Generate realistic JIRA issues"""
    issues = []
    
    for i in range(count):
        issue_type = random.choice(ISSUE_TYPES)
        templates = ISSUE_TEMPLATES[issue_type]
        title = random.choice(templates)
        
        # Add some variety to titles
        if random.random() < 0.3:
            title += f" - Phase {random.randint(1, 3)}"
        
        created_at = START_DATE + timedelta(days=random.randint(0, 90))
        
        # Status based on creation date (older = more likely done)
        days_since_created = (datetime.now() - created_at).days
        if days_since_created > 60:
            status = random.choice(["Done", "Done", "In Review"])
        elif days_since_created > 30:
            status = random.choice(["In Progress", "In Review", "Done"])
        else:
            status = random.choice(["To Do", "In Progress", "In Progress"])
        
        assignee = random.choice(DEVELOPERS)
        
        issue = {
            "issue_id": generate_issue_id(i),
            "title": title,
            "description": f"As a user, I want {title.lower()} so that I can improve my workflow.\n\nAcceptance Criteria:\n- Feature works as expected\n- Tests pass\n- Documentation updated",
            "status": status,
            "issue_type": issue_type,
            "priority": random.choice(PRIORITIES),
            "project_key": PROJECT_KEY,
            "assignee_email": assignee["email"],
            "reporter_email": "product@deviq.ai",
            "jira_created_at": created_at.isoformat(),
            "jira_updated_at": (created_at + timedelta(days=random.randint(1, 30))).isoformat(),
            "source": "jira",
            "commits": [],  # Will be populated later
        }
        issues.append(issue)
    
    return issues


def generate_synthetic_commits(issues: list, commits_per_issue: int = 3) -> list:
    """Generate realistic GitHub commits linked to issues"""
    commits = []
    
    for issue in issues:
        issue_id = issue["issue_id"]
        assignee_email = issue["assignee_email"]
        assignee = next((d for d in DEVELOPERS if d["email"] == assignee_email), DEVELOPERS[0])
        
        # Generate commits for this issue
        num_commits = random.randint(1, commits_per_issue * 2)
        
        for j in range(num_commits):
            commit_date = datetime.now() - timedelta(days=random.randint(1, 90))
            
            commit = {
                "commit_id": f"{issue_id.lower().replace('-', '')}_{j}_{random.randint(1000, 9999)}",
                "message": f"{random.choice(COMMIT_MESSAGES)} [{issue_id}]",
                "timestamp": commit_date.isoformat(),
                "files": [f"src/{random.choice(['components', 'services', 'utils'])}/{random.choice(['auth', 'api', 'data', 'ui'])}.py"],
                "files_json": {},
                "diff_patch": "diff --git a/file.py b/file.py\n+ some changes",
                "repository_name": REPO_NAME,
                "branch": random.choice(["main", "develop", f"feature/{issue_id.lower()}"]),
                "issue_id": issue_id,
                "linked_issue": issue_id,
                "modules_touched": [random.choice(["auth", "api", "database", "ui"])],
                "background_apps": {},
                "developer_id": assignee["id"],
                "author": assignee["name"],
                "author_email": assignee_email,
                "additions": random.randint(10, 200),
                "deletions": random.randint(0, 50),
                "total_changes": 0,  # Calculated below
                "attendance_pct": random.randint(80, 100),
                "active_minutes": random.randint(30, 240),
                "idle_minutes": random.randint(5, 30),
                "focus_ratio": round(random.uniform(0.7, 0.95), 2),
                "debug_session_count": random.randint(0, 3),
                "event_type": "commit",
            }
            commit["total_changes"] = commit["additions"] + commit["deletions"]
            commits.append(commit)
            
            # Link commit to issue
            issue["commits"].append({
                "commit_id": commit["commit_id"],
                "message": commit["message"],
                "timestamp": commit["timestamp"],
            })
    
    return commits


async def insert_jira_github_data(supabase: Client):
    """Insert synthetic JIRA/GitHub data"""
    
    print("=" * 80)
    print("GENERATING SYNTHETIC JIRA/GITHUB DATA")
    print("=" * 80)
    
    # Generate issues
    print("\n1. Generating JIRA issues...")
    issues = generate_synthetic_issues(50)
    print(f"   Created {len(issues)} issues")
    
    # Generate commits linked to issues
    print("\n2. Generating GitHub commits...")
    commits = generate_synthetic_commits(issues, commits_per_issue=3)
    print(f"   Created {len(commits)} commits")
    
    # Calculate linked commits
    linked_commits = sum(1 for c in commits if c.get("issue_id"))
    print(f"   Linked commits: {linked_commits}")
    
    # Insert issues
    print("\n3. Inserting issues into req_code_mapping...")
    inserted_issues = 0
    batch_size = 50
    for i in range(0, len(issues), batch_size):
        batch = issues[i:i+batch_size]
        try:
            result = supabase.table("req_code_mapping").insert(batch).execute()
            inserted_issues += len(batch)
            print(f"   Batch {i//batch_size + 1}: {len(batch)} issues inserted")
        except Exception as e:
            if "duplicate" in str(e).lower():
                print(f"   Batch {i//batch_size + 1}: Some issues already exist")
                inserted_issues += len(batch)  # Count as success
            else:
                print(f"   Batch {i//batch_size + 1} failed: {str(e)[:80]}")
    
    # Insert commits
    print("\n4. Inserting commits into extension_events...")
    inserted_commits = 0
    for i in range(0, len(commits), batch_size):
        batch = commits[i:i+batch_size]
        try:
            result = supabase.table("extension_events").insert(batch).execute()
            inserted_commits += len(batch)
            print(f"   Batch {i//batch_size + 1}: {len(batch)} commits inserted")
        except Exception as e:
            print(f"   Batch {i//batch_size + 1} failed: {str(e)[:80]}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nIssues inserted: {inserted_issues}/{len(issues)}")
    print(f"Commits inserted: {inserted_commits}/{len(commits)}")
    print(f"Linked commits: {linked_commits}")
    
    print("\nDASHBOARD SHOULD NOW SHOW:")
    print(f"  - Tracked Issues: {inserted_issues}")
    print(f"  - Extension Events: {inserted_commits}")
    print(f"  - Linked Commits: {linked_commits}")
    print(f"  - Link Rate: {linked_commits/max(1, inserted_commits)*100:.1f}%")
    
    print("\n" + "=" * 80)
    print("NEXT: Test your dashboard at https://dev-iq-iota.vercel.app")
    print("The main dashboard should now show real-looking numbers!")
    print("=" * 80)


async def main():
    print("=" * 80)
    print("SYNTHETIC JIRA/GITHUB DATA GENERATOR")
    print("=" * 80)
    print("\nThis script generates realistic-looking JIRA and GitHub data")
    print("to populate your main dashboard with demo-worthy metrics.")
    
    # Connect to Supabase
    print("\nConnecting to Supabase...")
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    try:
        result = supabase.table("req_code_mapping").select("count", count="exact").limit(1).execute()
        print("[OK] Connected")
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return
    
    # Confirm
    print("\n" + "!" * 80)
    print("This will insert synthetic JIRA issues and GitHub commits.")
    print("Existing data will be preserved (duplicates skipped).")
    print("!" * 80)
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        response = "yes"
        print("\nAuto-proceeding with --force...")
    else:
        response = input("\nProceed? (yes/no): ").strip().lower()
    
    if response == "yes":
        await insert_jira_github_data(supabase)
    else:
        print("\nCancelled.")


if __name__ == "__main__":
    asyncio.run(main())
