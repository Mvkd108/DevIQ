# DevHouse Extension - Pilot Operator Setup Guide

## Quick Start (5 Minutes)

This guide helps you deploy the DevHouse extension securely for a pilot deployment.

## Prerequisites

- VS Code installed
- Node.js and npm installed
- Supabase project URL and API key available
- Extension source code compiled

## Step 1: Compile the Extension

```powershell
cd C:\Users\madha\DevHouse26-main\DevHouse26-main\telemetry-extension
npm install
npm run compile
```

Verify: You should see `out/` directory with compiled JavaScript.

## Step 2: Launch Extension Development Host

1. Open `telemetry-extension` folder in VS Code
2. Press `F5` (or Run > Start Debugging)
3. Wait for Extension Development Host window to open

## Step 3: Configure Credentials (SECURE METHOD)

⚠️ **CRITICAL**: Use the secure command, NOT settings files!

In the Extension Development Host window:

1. Press `Ctrl+Shift+P` to open Command Palette
2. Type: `DevHouse: Configure Supabase Credentials`
3. Enter your Supabase URL: `https://your-project.supabase.co`
4. Enter your Supabase API Key (will be masked)
5. Click "Reload Window" when prompted

**Verify**: 
- Open Command Palette → `DevHouse: Show Data Collection Status`
- Should show "Upload: Ready" if credentials are valid

## Step 4: Configure Privacy Settings

Open VS Code Settings (`Ctrl+,`) and search for "devintel".

### For Initial Pilot (Recommended):

```json
{
  "devintel.telemetryEnabled": true,
  "devintel.presenceEnabled": false,
  "devintel.backgroundMonitoringEnabled": true,
  "devintel.showStatusBarSummary": true,
  "devintel.developerId": "your-name-or-id",
  "devintel.repositoryName": "your-repo-name"
}
```

### If Adding Camera Monitoring (Requires Consent):

```json
{
  "devintel.presenceEnabled": true,
  "devintel.pythonCommand": "python"  // or "py" on Windows
}
```

**Important**: Camera monitoring requires:
- Python with OpenCV installed
- Explicit user consent (dialog will appear on first use)
- Written consent from pilot participants

## Step 5: Verify Security

### Check 1: No Credentials in Settings Files

```powershell
# In workspace root
cat .vscode/settings.json | Select-String "supabase"
```

Should return NO matches or only show deprecated warnings.

### Check 2: Credentials are Secure

- Run: `DevHouse: Configure Supabase Credentials`
- URL should be shown (partially masked)
- Can update or clear without touching files

### Check 3: Test Upload

1. Make a code change in Extension Development Host
2. Create a git commit
3. Check DevHouse output channel for upload success
4. Verify in Supabase that `extension_events` table has new row

## Step 6: Test Privacy Features

### Test Camera Consent (if enabled):

1. Set `devintel.presenceEnabled` to `true`
2. Reload window
3. Should see consent dialog with privacy details
4. Try clicking "Deny" → setting should auto-disable
5. Re-enable and click "Allow" → monitoring should start

### Test Transparency Commands:

- `DevHouse: Show Data Collection Status` → See what's being tracked
- `DevHouse: Show Session Summary` → Review current session data
- `DevHouse: Open Transparency Center` → Full transparency UI
- `DevHouse: Reset Local Session State` → Clear session data

## Common Issues

### "Upload: Not Configured" in Status

**Cause**: Credentials not set or invalid

**Fix**:
1. Run `DevHouse: Configure Supabase Credentials`
2. Verify URL format: `https://xxx.supabase.co`
3. Verify API key is correct (check Supabase settings)

### Camera Consent Dialog Not Appearing

**Causes**:
- `presenceEnabled` is false (default)
- Consent already granted/denied
- Camera monitoring already running

**Fix**:
1. Check setting: `devintel.presenceEnabled`
2. To reset: delete `.vscode/` or use new workspace
3. Check output channel for "[PRESENCE]" messages

### Python Errors for Camera

**Symptoms**: "[PRESENCE] Presence helper could not run"

**Fix**:
1. Install Python: `winget install Python.Python.3.11`
2. Install OpenCV: `pip install opencv-python`
3. Set correct command: `devintel.pythonCommand` = `python` or `py`
4. Verify: `python -c "import cv2; print('OK')"`

### Credentials Leaked in Git

**Emergency Response**:
1. **Immediately rotate Supabase keys** (Supabase Dashboard → Settings → API)
2. Remove from git history:
   ```powershell
   git filter-branch --force --index-filter "git rm --cached --ignore-unmatch .vscode/settings.json" HEAD
   ```
3. Add to `.gitignore`:
   ```
   .vscode/settings.json
   ```
4. Use secure command for new credentials

## Pilot Deployment Checklist

Before deploying to pilot users:

- [ ] Extension compiles without errors
- [ ] Credentials configured via secure command
- [ ] No credentials in `.vscode/settings.json`
- [ ] `.gitignore` includes `.vscode/settings.json`
- [ ] Camera monitoring disabled by default (`presenceEnabled: false`)
- [ ] Transparency commands tested and working
- [ ] Upload to Supabase verified
- [ ] Consent process documented for pilot team
- [ ] Privacy policy shared with pilot users
- [ ] Incident response plan documented
- [ ] Security contact identified

## Pilot User Instructions

Share with pilot participants:

### Installation

1. Install the extension (provide .vsix or instructions)
2. Reload VS Code
3. Wait for configuration prompt

### First-Time Setup

1. Command Palette → `DevHouse: Configure Supabase Credentials`
2. Enter credentials provided by pilot administrator
3. Reload window

### Understanding Data Collection

- **Always collected locally**: Keystrokes, mouse activity (never uploaded)
- **Uploaded on commit**: Commit metadata, session duration, Jira issue
- **Optional (disabled by default)**: Camera presence, background apps

### Your Privacy Rights

- See collected data: `DevHouse: Show Data Collection Status`
- Clear session data: `DevHouse: Reset Local Session State`
- Disable features: Settings → "devintel"
- Opt out completely: Uninstall extension

## Monitoring & Maintenance

### Daily Checks

- Review Supabase `extension_events` table
- Check for upload errors in output logs
- Verify pilot users can see their data

### Weekly Reviews

- Review consent records
- Check for security incidents
- Update pilot users on findings

### Monthly Audits

- Full security audit
- Review data retention
- Update documentation

## Support

For pilot issues:
- Check output channel: View → Output → "DevHouse"
- Review logs in Supabase
- Contact: [Your support contact]

For security issues:
- See [SECURITY.md](./SECURITY.md)
- Report privately to security team

## Additional Resources

- [README.md](./README.md) - Full extension documentation
- [SECURITY.md](./SECURITY.md) - Security model and threat analysis
- [../docs/PILOT_READINESS_CHECKLIST.md](../docs/PILOT_READINESS_CHECKLIST.md) - Full pilot checklist
- [../docs/DEMO_OPERATOR_RUNBOOK.md](../docs/DEMO_OPERATOR_RUNBOOK.md) - Demo operation guide
