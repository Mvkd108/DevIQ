# DevHouse Telemetry Extension

**⚠️ SECURITY UPDATE (v0.0.2+)**: This extension now uses secure credential storage and requires explicit camera consent. See [SECURITY.md](./SECURITY.md) for details.

Use this guide when you want to test the VS Code extension by itself or add extension telemetry to a full DevHouse demo.

If you are new to the repo, start here first:

- [../docs/START_HERE.md](../docs/START_HERE.md)
- [../docs/FIRST_10_MINUTES.md](../docs/FIRST_10_MINUTES.md)

## What the extension does

The extension can:

- collect local commit-session signals
- let the developer select an active Jira issue
- show trust and session status inside VS Code
- upload commit telemetry to Supabase when configured

**Security Features**:
- 🔒 Secure credential storage (VS Code SecretStorage)
- ✋ Explicit camera consent required
- 👁️ Full transparency of collected data
- 🛡️ Local-only mode by default

Important routing rule:

- the extension uploads directly to Supabase
- it does not post through `backend/Req_codeMapping`

## Extension-only local testing

Use this path when you are not ready to stand up the full product yet.

### 1. Install and compile

```powershell
cd C:\Users\madha\DevHouse26-main\DevHouse26-main\telemetry-extension
npm install
npm run compile
```

### 2. Launch the extension

1. Open `telemetry-extension` in VS Code
2. Press `F5`
3. Wait for the Extension Development Host to open

### 3. Verify local-only behavior

You can validate these without any backend:

- command palette shows `DevHouse:*` commands
- status command opens trust/status guidance
- active issue picker opens
- transparency/session summary opens

**No credentials are needed for local-only testing**. Extension will show configuration guidance on first run.

## Full upload testing (SECURE METHOD)

⚠️ **IMPORTANT**: Never put credentials in VS Code settings files!

Use this path when you want the extension to create real `extension_events` rows in Supabase.

### Required prerequisites

- `backend/Req_codeMapping/sql/create_extension_events.sql` has been applied
- Supabase URL is known
- Supabase key is known

### Secure credential configuration

**Step 1**: Open Command Palette (Ctrl+Shift+P)

**Step 2**: Run: `DevHouse: Configure Supabase Credentials`

**Step 3**: Enter your Supabase URL and API Key when prompted
- URL format: `https://your-project.supabase.co`
- Key will be securely stored (not visible in settings)

**Step 4**: Reload window when prompted

**Step 5**: Verify configuration
- Run: `DevHouse: Show Data Collection Status`
- Should show "Upload: Ready"

### Recommended VS Code settings

Add settings like these to `.vscode/settings.json` (or user settings):

```json
{
  "devintel.developerId": "your-name",
  "devintel.repositoryName": "DevHouse26-main",
  "devintel.telemetryEnabled": true,
  "devintel.presenceEnabled": false,
  "devintel.backgroundMonitoringEnabled": true,
  "devintel.showStatusBarSummary": true,
  "devintel.pythonCommand": "py"
}
```

**DO NOT include these** (they are deprecated and insecure):
```json
// ❌ DO NOT USE - Insecure!
{
  "devintel.supabaseUrl": "...",  // Use command instead
  "devintel.supabaseKey": "..."   // Use command instead
}
```

Recommended first-run values:

- keep `devintel.presenceEnabled` off until Python is confirmed working
- keep `devintel.backgroundMonitoringEnabled` on if you want richer dashboard session context
- keep telemetry enabled if you want real upload validation

## Controlled pilot recommendation

For a small-team pilot, start with:

- `devintel.telemetryEnabled=true`
- `devintel.presenceEnabled=false` (explicitly disabled)
- `devintel.backgroundMonitoringEnabled=true` only if the team has explicitly agreed to it

**Camera monitoring requires**:
1. Setting `presenceEnabled` to true
2. User granting explicit consent via dialog
3. Python with OpenCV installed
4. Documented consent from pilot participants

Add presence monitoring later, not on day one.

## Security & Privacy

**Read [SECURITY.md](./SECURITY.md)** for complete security documentation.

Key points:
- Credentials stored securely in system keychain
- Camera requires explicit consent
- All data collection is transparent
- Local-only mode available
- No raw images/video ever collected

## Migrating from v0.0.1

If you have old configuration with credentials in settings:

1. Extension will auto-migrate on first activation
2. You'll see warnings to remove old settings
3. Open settings and DELETE `devintel.supabaseUrl` and `devintel.supabaseKey`
4. Verify with: `DevHouse: Show Data Collection Status`

## What healthy looks like

### Healthy local-only mode

- extension activates
- no upload configuration is required
- trust/status commands still work
- commit upload is skipped cleanly

### Healthy upload mode

- extension activates
- Supabase URL and key are set
- commit upload succeeds after a commit
- dashboard later shows the new activity after refresh or sync

## Demo sequence for extension plus dashboard

1. Confirm the main backend and dashboard are already working
2. Confirm `GET /api/dashboard` and `GET /api/delivery-timeline` already return JSON
3. Confirm `rollout_assessment.pilot.status` from `/api/health` is not `blocked`
4. Apply `create_extension_events.sql`
5. Compile the extension
6. Launch the Extension Development Host
7. Open a repo in the host window
8. Run `DevHouse: Select Active Jira Issue`
9. Make a commit
10. Refresh the dashboard or run sync
11. Confirm new activity appears

## Troubleshooting

### Extension not uploading

Check:

- Credentials configured via `DevHouse: Configure Supabase Credentials` (NOT in settings)
- `devintel.telemetryEnabled` is true
- `extension_events` exists in Supabase
- Run `DevHouse: Show Data Collection Status` to verify

### No Jira issue appears in the picker

The picker reads from `req_code_mapping`.

Check:

- Jira sync has already populated `req_code_mapping`
- Supabase credentials are correctly configured (use secure command)

### Presence monitoring errors

Check:

- `devintel.pythonCommand`
- Python is installed and visible to VS Code
- Camera consent was granted

If presence is not part of the demo, disable `devintel.presenceEnabled`.

### Camera consent dialog not appearing

This is expected behavior if:
- `devintel.presenceEnabled` is false (default)
- Consent was already granted/denied in this workspace
- To reset consent: delete workspace state or use new workspace

### Uploads still do not show in the dashboard

Check:

- extension upload actually succeeded
- dashboard backend points at the same Supabase project
- dashboard has refreshed since the commit
- `/api/dashboard` and `/api/delivery-timeline` were already healthy before the extension upload test

## Truthfulness note for demos

The extension provides real commit-session signals when it uploads successfully, but downstream timeline and summary views may still include inferred or mocked delivery stages depending on the rest of the product data.

Before presenting extension-backed dashboard output as customer evidence, review:

- [../docs/DATA_PROVENANCE.md](../docs/DATA_PROVENANCE.md)
- [../docs/FEATURE_MATURITY_MATRIX.md](../docs/FEATURE_MATURITY_MATRIX.md)
- [../docs/PILOT_READINESS_CHECKLIST.md](../docs/PILOT_READINESS_CHECKLIST.md)
- [../docs/DEMO_OPERATOR_RUNBOOK.md](../docs/DEMO_OPERATOR_RUNBOOK.md)
- [../docs/OPERATOR_CHEAT_SHEET.md](../docs/OPERATOR_CHEAT_SHEET.md)

Use [../docs/DEMO_OPERATOR_RUNBOOK.md](../docs/DEMO_OPERATOR_RUNBOOK.md) as the pilot operator checklist for extension-backed sessions; it spells out what to verify before/during/after the session and how to disclose which features are real, inferred, heuristic, or fallback/mock.
