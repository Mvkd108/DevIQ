# Security & Privacy Model

## Overview

The DevHouse Telemetry Extension is designed with security and privacy as core principles. This document explains how sensitive data is handled and what controls are available to users.

## Critical Security Improvements (v0.0.2+)

### 1. Secure Credential Storage

**Problem**: Previous versions stored Supabase credentials in VS Code settings (package.json defaults), which could be accidentally committed to source control.

**Solution**: All credentials are now stored using VS Code's SecretStorage API:
- Supabase URL and API keys are encrypted and stored in the system keychain
- Credentials are NEVER stored in workspace settings files
- Migration automatically moves old settings to secure storage

**Configuration**:
```
Use the command: "DevHouse: Configure Supabase Credentials"
```

**For Pilot Operators**:
1. Never use `devintel.supabaseUrl` or `devintel.supabaseKey` settings
2. Use the secure command to configure credentials
3. Verify `.vscode/settings.json` contains NO credentials

### 2. Camera Consent Flow

**Problem**: Previous versions started camera monitoring without explicit user consent.

**Solution**: Explicit opt-in consent flow:
- Camera access requires user consent via modal dialog on first use
- Clear explanation of what data is collected and why
- Consent is stored per-workspace
- Default setting changed from `true` to `false`
- No camera access until user clicks "Allow"

**What Users See**:
When camera monitoring is enabled for the first time:
1. Modal dialog explaining data collection
2. Clear privacy statements
3. "Allow" or "Deny" buttons
4. Option to review collected data anytime

**What Data is Collected**:
- ✅ Presence statistics (% present, check counts)
- ✅ Session duration
- ❌ Raw camera frames (NEVER collected)
- ❌ Screenshots (NEVER collected)
- ❌ Video recordings (NEVER collected)

## Data Collection Transparency

### What is Collected

| Data Type | Local Only | Can Upload | User Control |
|-----------|-----------|------------|--------------|
| Git commit events | ✅ | ✅ | `devintel.telemetryEnabled` |
| Presence statistics | ✅ | ✅ | `devintel.presenceEnabled` + consent |
| Background app summaries | ✅ | ✅ | `devintel.backgroundMonitoringEnabled` |
| Active Jira issue | ✅ | ✅ | Manual selection only |
| Keystroke/mouse activity | ✅ | ❌ | Always local only |
| File paths | ✅ | ✅ | Via commit metadata |

### What is NEVER Collected

- 🚫 Source code content (except commit messages you write)
- 🚫 Camera frames or images
- 🚫 Specific keystrokes
- 🚫 Screen content
- 🚫 Personal files outside workspace
- 🚫 Browser history
- 🚫 Passwords or secrets

## Configuration Security Levels

### Level 1: Fully Local (Default)
No credentials configured. All data stays local.

**Settings**:
```json
{
  "devintel.telemetryEnabled": true,
  "devintel.presenceEnabled": false,
  "devintel.backgroundMonitoringEnabled": false
}
```

**Use Case**: Personal development, evaluation, no upload needed

### Level 2: Upload-Ready (Pilot)
Credentials configured, basic telemetry enabled.

**Setup**:
1. Run: `DevHouse: Configure Supabase Credentials`
2. Enable settings:
```json
{
  "devintel.telemetryEnabled": true,
  "devintel.presenceEnabled": false,
  "devintel.backgroundMonitoringEnabled": true
}
```

**Use Case**: Small team pilot, commit tracking, no camera

### Level 3: Full Monitoring (Consent Required)
All features enabled with explicit consent.

**Setup**:
1. Configure credentials (see Level 2)
2. Enable all features:
```json
{
  "devintel.telemetryEnabled": true,
  "devintel.presenceEnabled": true,
  "devintel.backgroundMonitoringEnabled": true
}
```
3. Grant camera consent when prompted

**Use Case**: Full pilot with presence detection

## Operator Configuration Guide

### Initial Setup (Secure Method)

**Step 1**: Install Extension
```powershell
cd telemetry-extension
npm install
npm run compile
code .
# Press F5 to launch
```

**Step 2**: Configure Credentials Securely
1. In Extension Development Host, open Command Palette (Ctrl+Shift+P)
2. Run: `DevHouse: Configure Supabase Credentials`
3. Enter Supabase URL (e.g., https://xxx.supabase.co)
4. Enter API Key (will be hidden)
5. Reload window when prompted

**Step 3**: Configure Privacy Settings
1. Open Settings (Ctrl+,)
2. Search for "devintel"
3. Configure based on pilot requirements:
   - Start with camera monitoring OFF
   - Enable background monitoring only with team agreement

**Step 4**: Verify Security
1. Run: `DevHouse: Show Data Collection Status`
2. Verify no credentials in `.vscode/settings.json`
3. Check output channel for security confirmations

### Migration from Old Configuration

If you have existing settings with credentials:

1. Extension will auto-migrate on first run
2. You'll see warnings to remove old settings
3. Open settings and DELETE:
   - `devintel.supabaseUrl`
   - `devintel.supabaseKey`
4. Verify credentials work via "Show Data Collection Status"

### Verifying Secure Configuration

**Check 1**: No Credentials in Files
```powershell
# In workspace root
grep -r "supabase" .vscode/settings.json
# Should return NO matches or only "false" values
```

**Check 2**: Credentials in Secure Storage
- Run: `DevHouse: Configure Supabase Credentials`
- Should show current URL (partially masked)
- Can update or clear

**Check 3**: Camera Consent Status
- Enable `devintel.presenceEnabled`
- Should show consent dialog
- Check output channel for "[PRESENCE] Camera access consent"

## Privacy Controls for End Users

### View Collected Data
```
Command: "DevHouse: Show Data Collection Status"
```
Shows:
- What data is being collected
- Current session statistics
- Upload configuration status
- Privacy settings status

### Review Session Data
```
Command: "DevHouse: Show Session Summary"
```
Shows all data collected in current session before any upload.

### Reset Session Data
```
Command: "DevHouse: Reset Local Session State"
```
Clears all local session data including:
- Presence checks
- Activity counters
- Session start time

### Disable Features
All features can be disabled in settings:
- `devintel.telemetryEnabled`: Master switch for uploads
- `devintel.presenceEnabled`: Camera monitoring
- `devintel.backgroundMonitoringEnabled`: Background app tracking

### Complete Opt-Out
1. Disable all features in settings
2. Run: `DevHouse: Configure Supabase Credentials` → Clear credentials
3. Uninstall extension if desired

## Security Best Practices

### For Pilot Operators

1. **Never commit credentials**
   - Use secure command only
   - Review `.vscode/settings.json` before commits
   - Add to `.gitignore` if needed

2. **Document consent**
   - Get written consent before enabling camera
   - Explain data collection clearly
   - Provide opt-out instructions

3. **Regular audits**
   - Review "Data Collection Status" weekly
   - Verify no credential leaks
   - Check consent records

4. **Incident response**
   - If credentials leaked: rotate Supabase keys immediately
   - If consent violated: disable features immediately
   - Document and report incidents

### For Development Teams

1. **Test in local mode first**
   - No credentials needed
   - Verify features work locally
   - Review transparency features

2. **Staging environment**
   - Use separate Supabase project for testing
   - Never use production credentials in dev

3. **Code review checklist**
   - No hardcoded credentials
   - No new data collection without consent
   - All uploads clearly logged

## Threat Model

### Threats Mitigated

✅ **Credential Leakage**: SecretStorage prevents accidental commits
✅ **Unauthorized Camera Access**: Explicit consent required
✅ **Silent Data Collection**: All collection logged and visible
✅ **Data Exfiltration**: Only explicitly consented data uploads
✅ **Credential Exposure**: Passwords masked in UI

### Residual Risks

⚠️ **Local System Compromise**: If attacker has system access, SecretStorage can be accessed
⚠️ **Malicious Extensions**: Other extensions could potentially access VS Code APIs
⚠️ **Network Interception**: HTTPS required for Supabase (mitigated by using HTTPS)

### Out of Scope

❌ **Supabase Security**: Rely on Supabase's security model
❌ **Network Security**: Standard HTTPS encryption expected
❌ **Endpoint Security**: Host OS security is user's responsibility

## Compliance Notes

### GDPR Considerations

- **Data Minimization**: Only collect necessary data
- **Consent**: Explicit opt-in for camera monitoring
- **Right to Access**: "Show Data Collection Status" provides transparency
- **Right to Erasure**: "Reset Local Session State" clears data
- **Data Portability**: JSON format for collected data

### Enterprise Deployment

For enterprise pilots, consider:
1. Legal review of data collection practices
2. Written consent forms for camera monitoring
3. Data retention policies
4. Incident response procedures
5. Regular security audits

## Security Contact

For security issues:
1. Do NOT create public GitHub issues for security vulnerabilities
2. Contact DevHouse security team privately
3. Include "SECURITY" in email subject
4. Provide detailed reproduction steps

## Changelog

### v0.0.2 (Security Release)
- Added SecretStorage for credentials
- Added camera consent flow
- Changed presenceEnabled default to false
- Added credential migration
- Fixed broken test script
- Added SECURITY.md documentation

### v0.0.1
- Initial release with configuration-based credentials (insecure)
