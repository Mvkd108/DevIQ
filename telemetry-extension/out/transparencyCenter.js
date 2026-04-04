"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TransparencyCenter = void 0;
const vscode = require("vscode");
const extension_1 = require("./extension");
class TransparencyCenter {
    aggregator;
    activityMonitor;
    cameraMonitor;
    backgroundMonitor;
    jiraPicker;
    gitListener;
    constructor(aggregator, activityMonitor, cameraMonitor, backgroundMonitor, jiraPicker, gitListener) {
        this.aggregator = aggregator;
        this.activityMonitor = activityMonitor;
        this.cameraMonitor = cameraMonitor;
        this.backgroundMonitor = backgroundMonitor;
        this.jiraPicker = jiraPicker;
        this.gitListener = gitListener;
    }
    async showTransparencyOverview() {
        const content = await this.buildTransparencyMarkdown();
        const document = await vscode.workspace.openTextDocument({
            language: 'markdown',
            content
        });
        await vscode.window.showTextDocument(document, {
            preview: false,
            viewColumn: vscode.ViewColumn.Active
        });
    }
    async showSessionSummary() {
        const summary = await this.buildSessionSummaryMessage();
        const selection = await vscode.window.showInformationMessage(summary, 'Open Transparency Center', 'Reset Session', 'Show Data Status');
        if (selection === 'Open Transparency Center') {
            await this.showTransparencyOverview();
            return;
        }
        if (selection === 'Reset Session') {
            await this.resetSessionState();
            return;
        }
        if (selection === 'Show Data Status') {
            await this.showDataCollectionStatus();
        }
    }
    async showDataCollectionStatus() {
        const controls = this.getTrackingControls();
        await this.jiraPicker.ensureIssuesLoaded();
        const status = await this.buildQuickStatusMessage();
        const uploadBoundary = this.gitListener.getUploadBoundaryPreview();
        const selection = await vscode.window.showQuickPick(this.buildDataCollectionItems(status, controls, uploadBoundary), {
            title: 'DevHouse Data Collection Status',
            placeHolder: 'Review what stays local, what uploads on commit, and which controls are optional.'
        });
        if (!selection) {
            return;
        }
        switch (selection.action) {
            case 'status':
            case 'summary':
                await this.showSessionSummary();
                return;
            case 'settings':
                await vscode.commands.executeCommand('workbench.action.openSettings', 'devintel');
                return;
            case 'issue':
                await this.jiraPicker.showPicker();
                return;
            case 'transparency':
            case 'localOnly':
            case 'uploadedOnCommit':
            case 'neverUploaded':
                await this.showTransparencyOverview();
                return;
            default:
                return;
        }
    }
    async showActiveIssue() {
        await this.jiraPicker.ensureIssuesLoaded();
        const activeIssue = this.jiraPicker.getActiveIssue();
        if (!activeIssue) {
            const selection = await vscode.window.showInformationMessage('DevHouse: no active Jira issue is selected. Commits still stay local or upload normally, but the next commit will not be linked to Jira until you choose one.', 'Select Issue', 'Show Data Status');
            if (selection === 'Select Issue') {
                await this.jiraPicker.showPicker();
            }
            else if (selection === 'Show Data Status') {
                await this.showDataCollectionStatus();
            }
            return;
        }
        const description = activeIssue.description ? ` ${activeIssue.description}` : '';
        const selection = await vscode.window.showInformationMessage(`DevHouse issue: ${activeIssue.issue_id} (${activeIssue.status}) - ${activeIssue.title}.${description} It is only attached when a commit is prepared; nothing uploads continuously.`, 'Change Issue', 'Show Data Status');
        if (selection === 'Change Issue') {
            await this.jiraPicker.showPicker();
        }
        else if (selection === 'Show Data Status') {
            await this.showDataCollectionStatus();
        }
    }
    async manageTrackingSettings() {
        const controls = this.getTrackingControls();
        const optionalSignals = [
            controls.presenceEnabled ? 'presence summaries' : null,
            controls.backgroundMonitoringEnabled ? 'background summaries' : null
        ].filter(Boolean);
        const selection = await vscode.window.showQuickPick([
            {
                label: `${this.toggleIcon(controls.telemetryEnabled)} Telemetry upload`,
                description: 'User setting',
                detail: controls.telemetryEnabled
                    ? 'Commit data can be prepared on commit and uploaded only when Supabase is configured.'
                    : 'DevHouse stays local-only and skips commit uploads.'
            },
            {
                label: `${this.toggleIcon(controls.presenceEnabled)} Presence check`,
                description: 'User setting',
                detail: controls.presenceEnabled
                    ? 'Optional local presence summaries are enabled.'
                    : 'Optional local presence summaries are disabled.'
            },
            {
                label: `${this.toggleIcon(controls.backgroundMonitoringEnabled)} Background monitoring`,
                description: 'User setting',
                detail: controls.backgroundMonitoringEnabled
                    ? 'Optional whitelisted background-app summaries are enabled.'
                    : 'Optional whitelisted background-app summaries are disabled.'
            },
            {
                label: `${this.toggleIcon(controls.statusBarSummaryEnabled)} Status bar summary`,
                description: 'User setting',
                detail: controls.statusBarSummaryEnabled
                    ? 'A compact DevHouse summary is shown in the status bar.'
                    : 'The compact DevHouse status bar summary is hidden.'
            },
            {
                label: '$(settings-gear) Open DevHouse settings',
                description: 'Open Settings UI',
                detail: 'Review all DevHouse tracking controls in VS Code settings.'
            },
            {
                label: '$(book) Open Transparency Center',
                description: 'Review the current data story',
                detail: 'Open the full local-only vs uploaded-on-commit breakdown for this session.'
            }
        ], {
            placeHolder: `Choose a DevHouse setting to adjust. Optional sensitive signals currently enabled: ${optionalSignals.length > 0 ? optionalSignals.join(', ') : 'none'}.`
        });
        if (!selection) {
            return;
        }
        const config = vscode.workspace.getConfiguration('devintel');
        if (selection.label.includes('Telemetry upload')) {
            await config.update('telemetryEnabled', !controls.telemetryEnabled, vscode.ConfigurationTarget.Global);
            vscode.window.showInformationMessage(`DevHouse telemetry upload ${!controls.telemetryEnabled ? 'enabled' : 'disabled'}.`);
            return;
        }
        if (selection.label.includes('Presence check')) {
            await config.update('presenceEnabled', !controls.presenceEnabled, vscode.ConfigurationTarget.Global);
            vscode.window.showInformationMessage(`DevHouse presence summaries ${!controls.presenceEnabled ? 'enabled' : 'disabled'}.`);
            return;
        }
        if (selection.label.includes('Background monitoring')) {
            await config.update('backgroundMonitoringEnabled', !controls.backgroundMonitoringEnabled, vscode.ConfigurationTarget.Global);
            vscode.window.showInformationMessage(`DevHouse background monitoring ${!controls.backgroundMonitoringEnabled ? 'enabled' : 'disabled'}.`);
            return;
        }
        if (selection.label.includes('Status bar summary')) {
            await config.update('showStatusBarSummary', !controls.statusBarSummaryEnabled, vscode.ConfigurationTarget.Global);
            vscode.window.showInformationMessage(`DevHouse status bar summary ${!controls.statusBarSummaryEnabled ? 'enabled' : 'disabled'}.`);
            return;
        }
        if (selection.label.includes('Open DevHouse settings')) {
            await vscode.commands.executeCommand('workbench.action.openSettings', 'devintel');
            return;
        }
        await this.showTransparencyOverview();
    }
    async resetSessionState() {
        const selection = await vscode.window.showWarningMessage('Reset local DevHouse session metrics, presence summaries, and background monitoring state?', { modal: true }, 'Reset Session');
        if (selection !== 'Reset Session') {
            return;
        }
        this.aggregator.resetSession();
        this.activityMonitor.resetTracker();
        this.cameraMonitor.resetSession();
        this.backgroundMonitor.resetSession();
        extension_1.logger.appendLine('[SESSION] Local session state was reset by the developer.');
        vscode.window.showInformationMessage('DevHouse: local session counters and summaries were reset. Active Jira selection was kept.');
    }
    getTrackingControls() {
        const config = vscode.workspace.getConfiguration('devintel');
        const supabaseUrl = config.get('supabaseUrl', '');
        const supabaseKey = config.get('supabaseKey', '');
        return {
            telemetryEnabled: config.get('telemetryEnabled', true),
            presenceEnabled: config.get('presenceEnabled', true),
            backgroundMonitoringEnabled: config.get('backgroundMonitoringEnabled', true),
            uploadConfigured: Boolean(supabaseUrl && supabaseKey),
            statusBarSummaryEnabled: config.get('showStatusBarSummary', true)
        };
    }
    async buildTransparencyMarkdown() {
        const controls = this.getTrackingControls();
        await this.jiraPicker.ensureIssuesLoaded();
        const session = this.aggregator.getSession();
        const openedFiles = this.activityMonitor.getOpenedFiles().map(file => vscode.workspace.asRelativePath(file, false));
        const modifiedFiles = this.activityMonitor.getModifiedFiles().map(file => vscode.workspace.asRelativePath(file, false));
        const presence = this.cameraMonitor.getStatus();
        const background = this.backgroundMonitor.getStatus();
        const nextCommitPreviews = await this.gitListener.getNextCommitPreview();
        const activeIssue = this.jiraPicker.getActiveIssue();
        const sessionStart = this.getSessionStart(session.session_id);
        const trackedRepositories = nextCommitPreviews.map(preview => preview.repositoryName);
        const uploadBoundary = this.gitListener.getUploadBoundaryPreview();
        const optionalSignals = [
            controls.presenceEnabled ? 'presence summaries' : null,
            controls.backgroundMonitoringEnabled ? 'background summaries' : null
        ].filter(Boolean);
        const uploadReady = controls.telemetryEnabled && controls.uploadConfigured;
        const issueSummary = activeIssue
            ? `${activeIssue.issue_id} (${activeIssue.status})${activeIssue.title ? ` - ${activeIssue.title}` : ''}`
            : 'None selected';
        const uploadStory = uploadReady
            ? 'DevHouse is ready to prepare an upload when the next commit is detected.'
            : controls.telemetryEnabled
                ? 'DevHouse is tracking locally, but uploads stay off until Supabase settings are configured.'
                : 'DevHouse is running in local-only mode because telemetry upload is disabled.';
        const lines = [
            '# DevHouse Transparency Center',
            '',
            `Updated: ${new Date().toLocaleString()}`,
            '',
            '## Pilot Snapshot',
            '',
            `- Active Jira issue: ${issueSummary}`,
            `- Repositories in scope: ${this.inlineList(trackedRepositories, 'No tracked repository detected yet')}`,
            `- Telemetry upload: ${this.enabledLabel(controls.telemetryEnabled)}${controls.uploadConfigured ? '' : ' (Supabase not configured)'}`,
            `- Presence tracking: ${this.enabledLabel(controls.presenceEnabled)}`,
            `- Background monitoring: ${this.enabledLabel(controls.backgroundMonitoringEnabled)}`,
            `- Optional sensitive signals currently enabled: ${optionalSignals.length > 0 ? optionalSignals.join(', ') : 'None'}`,
            `- Status bar summary: ${this.enabledLabel(controls.statusBarSummaryEnabled)}`,
            `- Next commit upload readiness: ${uploadStory}`,
            '',
            '## Current Session Metrics',
            '',
            `- Session started: ${sessionStart ? sessionStart.toLocaleString() : 'Unknown'}`,
            `- Session age: ${this.formatDurationFromMinutes(this.getSessionAgeMinutes(sessionStart))}`,
            `- Active editing time: ${session.editing_duration_minutes} minute(s)`,
            `- Idle time: ${session.idle_minutes} minute(s)`,
            `- Focus ratio: ${Math.round(session.focus_ratio * 100)}%`,
            `- Files opened: ${session.files_opened}`,
            `- Files modified: ${session.files_modified}`,
            `- Lines changed: +${session.lines_added} / -${session.lines_deleted}`,
            `- Debug sessions started: ${session.debug_session_count}`,
            `- Modified files this session: ${this.inlineList(modifiedFiles, 'None yet')}`,
            `- Opened files this session: ${this.inlineList(openedFiles, 'None yet')}`,
            '',
            '## What DevHouse Uses',
            '',
            '- Nothing is uploaded continuously. DevHouse only prepares an upload when a commit is detected and telemetry upload is enabled.',
            '- Measured locally: file opens, modified-file count, line changes, active time, idle time, and debug session count for this session.',
            '- Inferred locally: focus ratio from VS Code window focus changes, and presence attendance from local presence checks when enabled.',
            '- Selected by you: the active Jira issue, if you choose one, so the next commit can be linked intentionally.',
            `- Optional presence summary: ${presence.enabled ? 'enabled' : 'disabled'}. Raw camera frames are not uploaded; only summary counts can be attached to a commit event.`,
            `- Optional background-app summary: ${background.enabled ? 'enabled' : 'disabled'}. Only whitelisted app names plus timing summaries can be attached to a commit event.`,
            '',
            '## Local Computation And Storage',
            '',
            ...this.renderBoundarySection(uploadBoundary.localOnly),
            '',
            '## Presence Summary',
            '',
            `- Status: ${this.enabledLabel(presence.enabled)}`,
            `- Attendance: ${presence.attendance_pct}% (${presence.present_checks}/${presence.total_checks} checks present)`,
            `- Session duration: ${Math.floor(presence.session_duration_seconds / 60)} minute(s)`,
            `- Last check: ${presence.lastCheckAt ? `${presence.lastCheckAt} (${presence.lastCheckResult ? 'present' : 'not detected'})` : 'No checks recorded yet'}`,
            '',
            '## Background Monitoring Summary',
            '',
            `- Status: ${this.enabledLabel(background.enabled)}`,
            `- Last scan: ${background.lastScanAt ?? 'No scans recorded yet'}`,
            `- Tracked apps this session: ${background.trackedApps.length > 0 ? background.trackedApps.map(app => `${app.app_name} (${app.duration_seconds}s)`).join(', ') : 'None yet'}`,
            `- Whitelisted apps: ${this.inlineList(background.whitelistedApps, 'No whitelist configured')}`,
            '',
            '## Next Commit Upload Preview',
            ''
        ];
        if (nextCommitPreviews.length === 0) {
            lines.push('- No Git repositories are currently being tracked by the extension.');
        }
        else {
            for (const preview of nextCommitPreviews) {
                lines.push(...this.renderNextCommitPreview(preview, controls, session, activeIssue?.issue_id ?? null, presence, background));
            }
        }
        lines.push('', '## Data Boundaries', '', '- Local only:', ...this.renderBoundarySection(uploadBoundary.localOnly), '', '- Uploaded on commit when telemetry upload is enabled and configured:', ...this.renderBoundarySection(uploadBoundary.uploadedOnCommit), '', '- Optional when enabled and excluded when disabled:', ...this.renderBoundarySection(uploadBoundary.optionalWhenEnabled), '', '## Never Uploaded', '', ...this.renderBoundarySection(uploadBoundary.neverUploaded), '', '## Useful Commands', '', '- `DevHouse: Open Transparency Center`', '- `DevHouse: Show Session Summary`', '- `DevHouse: Show Data Collection Status`', '- `DevHouse: Show Active Issue`', '- `DevHouse: Manage Tracking Settings`', '- `DevHouse: Open Settings`', '- `DevHouse: Reset Session State`');
        return lines.join('\n');
    }
    renderNextCommitPreview(preview, controls, session, activeIssueId, presence, background) {
        const uploadReady = controls.telemetryEnabled && controls.uploadConfigured;
        const uploadSummary = uploadReady
            ? 'A commit event will be prepared for upload when the next commit is detected.'
            : controls.telemetryEnabled
                ? 'No upload will happen until Supabase settings are configured, so this stays local-only.'
                : 'No upload will happen because telemetry upload is disabled, so this stays local-only.';
        const lines = [
            `### ${preview.repositoryName}`,
            '',
            `- Repository: \`${preview.repositoryPath}\``,
            `- Branch: ${preview.branch}`,
            `- Upload status: ${uploadSummary}`,
            `- Active issue to attach: ${activeIssueId ?? 'None selected'}`,
            `- Session summary to attach: ${uploadReady ? `active ${session.editing_duration_minutes}m, idle ${session.idle_minutes}m, focus ${Math.round(session.focus_ratio * 100)}%, +${session.lines_added} / -${session.lines_deleted}, debug ${session.debug_session_count}` : 'Local only until upload is enabled and configured.'}`,
            `- Presence summary to attach: ${uploadReady && presence.enabled ? `${presence.attendance_pct}% attendance across ${presence.total_checks} checks` : 'Not uploaded on the next commit.'}`,
            `- Background summary to attach: ${uploadReady && background.enabled ? `${background.trackedApps.length} whitelisted app(s)` : 'Not uploaded on the next commit.'}`,
            `- Commit-specific data added at commit time: ${uploadReady ? 'commit id, author, message, branch, committed file list, and per-file patches for committed files.' : 'Nothing uploads here right now; the working-tree preview below stays local.'}`,
            `- Pending local JSON events waiting to sync: ${preview.pendingLocalEventCount}`,
            `- Current working tree preview: ${this.inlineList(preview.changedFiles, 'No modified tracked files detected right now')}`,
            ''
        ];
        return lines;
    }
    enabledLabel(enabled) {
        return enabled ? 'Enabled' : 'Disabled';
    }
    async buildQuickStatusMessage() {
        const controls = this.getTrackingControls();
        await this.jiraPicker.ensureIssuesLoaded();
        const session = this.aggregator.getSession();
        const activeIssue = this.jiraPicker.getActiveIssue();
        const nextCommitPreviews = await this.gitListener.getNextCommitPreview();
        const uploadBoundary = this.gitListener.getUploadBoundaryPreview();
        const repositories = nextCommitPreviews.map(preview => preview.repositoryName);
        const optionalSignals = [
            controls.presenceEnabled ? 'presence' : null,
            controls.backgroundMonitoringEnabled ? 'background monitoring' : null
        ].filter(Boolean).join(', ') || 'none';
        const uploadReady = controls.telemetryEnabled && controls.uploadConfigured;
        const uploadState = uploadReady
            ? 'upload ready on next commit'
            : controls.telemetryEnabled
                ? 'local-only until upload settings are configured'
                : 'upload disabled';
        return `DevHouse: repos ${this.inlineList(repositories, 'none')}; issue ${activeIssue?.issue_id ?? 'none'}; telemetry ${controls.telemetryEnabled ? 'on' : 'off'}; optional signals ${optionalSignals}; active ${session.editing_duration_minutes}m; ${uploadState}; ${uploadBoundary.localOnly.length} local-only categories; ${uploadBoundary.uploadedOnCommit.length} uploaded-on-commit categories.`;
    }
    async buildSessionSummaryMessage() {
        const controls = this.getTrackingControls();
        const session = this.aggregator.getSession();
        const activeIssue = this.jiraPicker.getActiveIssueId() ?? 'none';
        const modifiedFiles = this.activityMonitor.getModifiedFiles().map(file => vscode.workspace.asRelativePath(file, false));
        const sessionStart = this.getSessionStart(session.session_id);
        const uploadConfigured = controls.telemetryEnabled && controls.uploadConfigured;
        return `DevHouse session: started ${sessionStart ? sessionStart.toLocaleTimeString() : 'unknown'}; active ${session.editing_duration_minutes}m; idle ${session.idle_minutes}m; focus ${Math.round(session.focus_ratio * 100)}%; modified files ${session.files_modified}; lines +${session.lines_added}/-${session.lines_deleted}; issue ${activeIssue}; upload ${uploadConfigured ? 'ready on next commit' : controls.telemetryEnabled ? 'local-only until Supabase is set' : 'disabled'}; recent files ${this.inlineList(modifiedFiles, 'none yet')}.`;
    }
    buildDataCollectionItems(status, controls, uploadBoundary) {
        const optionalSignals = [
            controls.presenceEnabled ? 'presence summaries' : null,
            controls.backgroundMonitoringEnabled ? 'background summaries' : null
        ].filter(Boolean);
        return [
            {
                label: '$(info) Status snapshot',
                description: 'Current session and upload readiness',
                detail: status,
                action: 'status'
            },
            {
                label: '$(shield) Open Transparency Center',
                description: 'Full trust and data-boundary report',
                detail: 'Open the markdown view with per-session metrics and explicit local-only, uploaded-on-commit, and never-uploaded sections.',
                action: 'transparency'
            },
            {
                label: '$(graph) Open Session Summary',
                description: 'Short operational summary',
                detail: 'Show active/idle/focus metrics and next-commit upload readiness.',
                action: 'summary'
            },
            {
                label: '$(tag) Select Active Jira Issue',
                description: 'Control which issue is attached to the next commit',
                detail: 'Issue id is only attached if you select one. Commits can still be tracked without a Jira link.',
                action: 'issue'
            },
            {
                label: '$(settings-gear) Open DevHouse Settings',
                description: 'Configure telemetry and optional sensitive signals',
                detail: `Optional sensitive signals currently enabled: ${optionalSignals.length > 0 ? optionalSignals.join(', ') : 'none'}.`,
                action: 'settings'
            },
            {
                label: '$(cloud-upload) Uploaded on commit',
                description: 'High-level upload contract',
                detail: uploadBoundary.uploadedOnCommit.join(' | '),
                action: 'uploadedOnCommit'
            },
            {
                label: '$(device-camera) Local-only data',
                description: 'Data that stays on your machine',
                detail: uploadBoundary.localOnly.join(' | '),
                action: 'localOnly'
            },
            {
                label: '$(lock) Never uploaded',
                description: 'Privacy guarantee',
                detail: uploadBoundary.neverUploaded.join(' | '),
                action: 'neverUploaded'
            }
        ];
    }
    renderBoundarySection(items) {
        if (items.length === 0) {
            return ['- None recorded'];
        }
        return items.map(item => `- ${item}`);
    }
    getSessionStart(sessionId) {
        const match = sessionId.match(/^sess_(\d+)$/);
        if (!match) {
            return null;
        }
        const timestamp = Number(match[1]);
        if (!Number.isFinite(timestamp)) {
            return null;
        }
        return new Date(timestamp);
    }
    getSessionAgeMinutes(sessionStart) {
        if (!sessionStart) {
            return 0;
        }
        return Math.max(0, Math.floor((Date.now() - sessionStart.getTime()) / 60000));
    }
    formatDurationFromMinutes(totalMinutes) {
        const hours = Math.floor(totalMinutes / 60);
        const minutes = totalMinutes % 60;
        if (hours <= 0) {
            return `${minutes} minute(s)`;
        }
        return `${hours}h ${minutes}m`;
    }
    inlineList(items, fallback) {
        if (items.length === 0) {
            return fallback;
        }
        return items.slice(0, 8).join(', ') + (items.length > 8 ? `, +${items.length - 8} more` : '');
    }
    toggleIcon(enabled) {
        return enabled ? '$(check)' : '$(circle-slash)';
    }
}
exports.TransparencyCenter = TransparencyCenter;
//# sourceMappingURL=transparencyCenter.js.map