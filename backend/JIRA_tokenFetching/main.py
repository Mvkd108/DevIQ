import os
from datetime import datetime, timezone

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from routers import jira
from services.jira_sync import JiraClient, JiraConfigError

load_dotenv()


def parse_allowed_origins() -> list[str]:
    configured = os.getenv("ALLOWED_ORIGINS", "")
    parsed = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]

    default_origins = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]

    allow_all = os.getenv("ALLOW_ALL_CORS", "false").strip().lower() == "true"
    if allow_all:
        return ["*"]

    seen: set[str] = set()
    origins: list[str] = []
    for origin in [*default_origins, *parsed]:
        if origin and origin not in seen:
            origins.append(origin)
            seen.add(origin)
    return origins


APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
AUTO_SYNC_ON_STARTUP = os.getenv("AUTO_SYNC_ON_STARTUP", "false").strip().lower() == "true"
ALLOWED_ORIGINS = parse_allowed_origins()

app = FastAPI(title="DevPulse Jira Sync Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials="*" not in ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jira.router)


@app.on_event("startup")
async def startup_event():
    if not AUTO_SYNC_ON_STARTUP:
        print("[INFO] Startup sync skipped. Set AUTO_SYNC_ON_STARTUP=true to enable.")
        return

    print("[INFO] Startup sync enabled. Triggering Jira sync.")
    try:
        client = JiraClient()
        count = client.sync_all_tickets()
        print(f"[INFO] Startup sync complete. Synced {count} tickets.")
    except JiraConfigError as exc:
        print(f"[WARN] Startup sync skipped due to missing configuration: {exc}")
    except Exception as exc:
        print(f"[ERROR] Startup sync failed: {exc}")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/health")
def health_check():
    required_vars = [
        "JIRA_URL",
        "JIRA_EMAIL",
        "JIRA_TOKEN",
        "JIRA_PROJECT",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
    ]
    missing = [name for name in required_vars if not os.getenv(name)]

    return {
        "status": "ok" if not missing else "degraded",
        "service": "devpulse-jira-sync",
        "environment": APP_ENV,
        "auto_sync_on_startup": AUTO_SYNC_ON_STARTUP,
        "allowed_origins": ALLOWED_ORIGINS,
        "missing_configuration": missing,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
