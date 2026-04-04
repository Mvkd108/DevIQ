import os
from typing import List, Optional

import requests
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


class JiraConfigError(RuntimeError):
    pass


class JiraClient:
    def __init__(self):
        self.url = os.getenv("JIRA_URL", "").rstrip("/")
        self.email = os.getenv("JIRA_EMAIL", "")
        self.token = os.getenv("JIRA_TOKEN", "")
        self.project = os.getenv("JIRA_PROJECT", "")
        self.timeout_seconds = int(os.getenv("JIRA_HTTP_TIMEOUT_SECONDS", "20"))
        self.auth = (self.email, self.token)

        sb_url = os.getenv("SUPABASE_URL", "")
        sb_key = os.getenv("SUPABASE_SERVICE_KEY", "")

        self._validate_required_config(sb_url, sb_key)
        self.supabase: Client = create_client(sb_url, sb_key)

    def _validate_required_config(self, sb_url: str, sb_key: str) -> None:
        missing = []
        if not self.url:
            missing.append("JIRA_URL")
        if not self.email:
            missing.append("JIRA_EMAIL")
        if not self.token:
            missing.append("JIRA_TOKEN")
        if not self.project:
            missing.append("JIRA_PROJECT")
        if not sb_url:
            missing.append("SUPABASE_URL")
        if not sb_key:
            missing.append("SUPABASE_SERVICE_KEY")

        if missing:
            raise JiraConfigError(f"Missing required environment variables: {', '.join(missing)}")

    def parse_adf_to_text(self, adf: Optional[dict]) -> str:
        if not adf:
            return ""

        text_parts = []

        def walk(node):
            if node.get("type") == "text":
                text_parts.append(node.get("text", ""))
            elif "content" in node:
                for child in node["content"]:
                    walk(child)

        walk(adf)
        return "".join(text_parts)

    def get_issue_data(self, issue: dict) -> dict:
        fields = issue.get("fields", {})
        return {
            "issue_id": issue.get("key"),
            "title": fields.get("summary", ""),
            "description": self.parse_adf_to_text(fields.get("description")),
            "status": fields.get("status", {}).get("name"),
            "issue_type": fields.get("issuetype", {}).get("name"),
            "priority": fields.get("priority", {}).get("name"),
            "project_key": fields.get("project", {}).get("key"),
            "assignee_email": fields.get("assignee", {}).get("emailAddress") if fields.get("assignee") else None,
            "reporter_email": fields.get("reporter", {}).get("emailAddress") if fields.get("reporter") else None,
            "jira_created_at": fields.get("created"),
            "jira_updated_at": fields.get("updated"),
        }

    def upsert_to_supabase(self, records: List[dict]):
        if not records:
            return

        try:
            self.supabase.table("req_code_mapping").upsert(records, on_conflict="issue_id").execute()
        except Exception as exc:
            print(f"[ERROR] Supabase upsert failed: {exc}")
            raise

    def delete_from_supabase(self, issue_id: str):
        if not issue_id:
            return

        try:
            self.supabase.table("req_code_mapping").delete().eq("issue_id", issue_id).execute()
        except Exception as exc:
            print(f"[ERROR] Supabase delete failed for {issue_id}: {exc}")
            raise

    def delete_missing_project_issues(self, active_issue_ids: set[str]):
        if not self.project:
            return

        try:
            response = (
                self.supabase.table("req_code_mapping")
                .select("issue_id")
                .eq("project_key", self.project)
                .execute()
            )
            existing_issue_ids = {
                row["issue_id"]
                for row in (response.data or [])
                if row.get("issue_id")
            }
            stale_issue_ids = existing_issue_ids - active_issue_ids

            for issue_id in stale_issue_ids:
                print(f"[DEBUG] Removing stale issue from Supabase: {issue_id}")
                self.delete_from_supabase(issue_id)
        except Exception as exc:
            print(f"[ERROR] Failed to reconcile deleted Jira issues for project {self.project}: {exc}")

    def _post_jira(self, url: str, payload: dict) -> requests.Response:
        try:
            response = requests.post(url, json=payload, auth=self.auth, timeout=self.timeout_seconds)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise RuntimeError(f"Jira request failed: {exc}") from exc

    def sync_all_tickets(self) -> int:
        synced_count = 0
        next_page_token = None
        max_results = 100
        active_issue_ids: set[str] = set()

        search_url = f"{self.url}/rest/api/3/search/jql"
        print(f"[DEBUG] Hitting Jira URL: {search_url}")

        while True:
            payload = {
                "jql": f"project='{self.project}'",
                "fields": [
                    "summary",
                    "description",
                    "status",
                    "issuetype",
                    "priority",
                    "project",
                    "assignee",
                    "reporter",
                    "created",
                    "updated",
                ],
                "maxResults": max_results,
            }

            if next_page_token:
                payload["nextPageToken"] = next_page_token

            response = self._post_jira(search_url, payload)
            data = response.json()
            issues = data.get("issues", [])
            print(f"[DEBUG] Fetched {len(issues)} issues from Jira")

            if not issues:
                print(f"[DEBUG] No issues found in this page for project {self.project}")
                if not next_page_token and synced_count == 0:
                    self.delete_missing_project_issues(active_issue_ids)
                break

            records = [self.get_issue_data(issue) for issue in issues]
            active_issue_ids.update(
                record["issue_id"]
                for record in records
                if record.get("issue_id")
            )
            print(f"[DEBUG] Attempting to upsert {len(records)} records to Supabase")
            self.upsert_to_supabase(records)

            synced_count += len(issues)
            next_page_token = data.get("nextPageToken")

            if not next_page_token:
                break

        self.delete_missing_project_issues(active_issue_ids)
        print(f"[DEBUG] Sync completed. Total synced: {synced_count}")
        return synced_count
