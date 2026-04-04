"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.StatusBarSummary = void 0;
const vscode = require("vscode");
class StatusBarSummary {
    aggregator;
    cameraMonitor;
    backgroundMonitor;
    jiraPicker;
    gitListener;
    item;
    intervalId;
    disposables = [];
    constructor(aggregator, cameraMonitor, backgroundMonitor, jiraPicker, gitListener) {
        this.aggregator = aggregator;
        this.cameraMonitor = cameraMonitor;
        this.backgroundMonitor = backgroundMonitor;
        this.jiraPicker = jiraPicker;
        this.gitListener = gitListener;
        this.item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        this.item.command = 'devhouse.showDataCollectionStatus';
        this.item.name = 'DevHouse Session Summary';
        this.disposables.push(vscode.workspace.onDidChangeConfiguration((event) => {
            if (event.affectsConfiguration('devintel')) {
                this.refresh();
            }
        }));
        this.intervalId = setInterval(() => {
            this.refresh();
        }, 30000);
        this.refresh();
    }
    refresh() {
        const config = vscode.workspace.getConfiguration('devintel');
        const showStatusBarSummary = config.get('showStatusBarSummary', true);
        if (!showStatusBarSummary) {
            this.item.hide();
            return;
        }
        const session = this.aggregator.getSession();
        const telemetryEnabled = config.get('telemetryEnabled', true);
        const uploadConfigured = Boolean(config.get('supabaseUrl', '') && config.get('supabaseKey', ''));
        const issue = this.jiraPicker.getActiveIssueId() ?? 'No issue';
        const presence = this.cameraMonitor.isEnabled();
        const background = this.backgroundMonitor.isEnabled();
        const uploadBoundary = this.gitListener.getUploadBoundaryPreview();
        const state = this.getStatusBarState(telemetryEnabled, uploadConfigured, issue !== 'No issue');
        const issueLabel = issue === 'No issue' ? 'No issue selected' : issue;
        const trackingLabel = `T${telemetryEnabled ? '+' : '-'} P${presence ? '+' : '-'} B${background ? '+' : '-'}`;
        const boundaryLabel = `${uploadBoundary.localOnly.length}L/${uploadBoundary.uploadedOnCommit.length}U`;
        this.item.text = `$(shield) DH ${issueLabel} • ${state.label} • ${trackingLabel} • ${boundaryLabel}`;
        this.item.backgroundColor = state.backgroundColor;
        this.item.tooltip = this.buildTooltip(issue, session, telemetryEnabled, uploadConfigured, presence, background, state.text, uploadBoundary);
        this.item.show();
    }
    dispose() {
        clearInterval(this.intervalId);
        this.item.dispose();
        this.disposables.forEach((disposable) => disposable.dispose());
    }
    buildTooltip(issue, session, telemetryEnabled, uploadConfigured, presenceEnabled, backgroundEnabled, uploadReadiness, uploadBoundary) {
        const tooltip = new vscode.MarkdownString(undefined, true);
        tooltip.appendMarkdown('**DevHouse Transparency Summary**\n\n');
        tooltip.appendMarkdown(`- Active issue: ${issue}\n`);
        tooltip.appendMarkdown(`- Active editing time: ${session.editing_duration_minutes} minute(s)\n`);
        tooltip.appendMarkdown(`- Telemetry upload: ${telemetryEnabled ? 'enabled' : 'disabled'}\n`);
        tooltip.appendMarkdown(`- Upload readiness: ${uploadReadiness}\n`);
        tooltip.appendMarkdown(`- Upload configured: ${uploadConfigured ? 'yes' : 'no'}\n`);
        tooltip.appendMarkdown(`- Presence summary: ${presenceEnabled ? 'enabled' : 'disabled'}\n`);
        tooltip.appendMarkdown(`- Background summary: ${backgroundEnabled ? 'enabled' : 'disabled'}\n`);
        tooltip.appendMarkdown(`- Optional sensitive signals enabled: ${this.describeSensitiveSignals(presenceEnabled, backgroundEnabled)}\n`);
        tooltip.appendMarkdown('- Status labels: `T` telemetry, `P` presence, `B` background monitoring, `L/U` local-only vs uploaded-on-commit categories.\n');
        tooltip.appendMarkdown('- Nothing uploads continuously. Data is only uploaded when a commit is detected and telemetry upload is enabled.\n\n');
        tooltip.appendMarkdown(`- Local only: ${this.inlinePreview(uploadBoundary.localOnly)}\n`);
        tooltip.appendMarkdown(`- Uploaded on commit: ${this.inlinePreview(uploadBoundary.uploadedOnCommit)}\n`);
        tooltip.appendMarkdown(`- Never uploaded: ${this.inlinePreview(uploadBoundary.neverUploaded)}\n\n`);
        tooltip.appendMarkdown('Click to open the transparency center.');
        return tooltip;
    }
    getStatusBarState(telemetryEnabled, uploadConfigured, hasActiveIssue) {
        if (!telemetryEnabled) {
            return {
                label: 'Local only',
                text: 'telemetry upload is off; commit data stays local and nothing uploads',
                backgroundColor: new vscode.ThemeColor('statusBarItem.warningBackground')
            };
        }
        if (!uploadConfigured) {
            return {
                label: 'Config needed',
                text: 'Supabase settings are missing, so DevHouse stays local-only until upload and Jira sync are configured',
                backgroundColor: new vscode.ThemeColor('statusBarItem.warningBackground')
            };
        }
        if (!hasActiveIssue) {
            return {
                label: 'Pick Jira',
                text: 'tracking is healthy; select a Jira issue if you want the next commit linked',
                backgroundColor: new vscode.ThemeColor('statusBarItem.warningBackground')
            };
        }
        return {
            label: 'Ready on commit',
            text: 'tracking is healthy and the next commit can be prepared for upload',
            backgroundColor: new vscode.ThemeColor('statusBarItem.prominentBackground')
        };
    }
    describeSensitiveSignals(presenceEnabled, backgroundEnabled) {
        const enabled = [
            presenceEnabled ? 'presence' : null,
            backgroundEnabled ? 'background monitoring' : null
        ].filter(Boolean);
        if (enabled.length === 0) {
            return 'none';
        }
        return enabled.join(', ');
    }
    inlinePreview(items) {
        if (items.length === 0) {
            return 'none';
        }
        const preview = items.slice(0, 2).join('; ');
        return items.length > 2 ? `${preview}; +${items.length - 2} more` : preview;
    }
}
exports.StatusBarSummary = StatusBarSummary;
//# sourceMappingURL=statusBarSummary.js.map