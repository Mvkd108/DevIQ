"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.logger = void 0;
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const signalAggregator_1 = require("./signalAggregator");
const activityMonitor_1 = require("./activityMonitor");
const backgroundMonitor_1 = require("./backgroundMonitor");
const webhookSender_1 = require("./webhookSender");
const gitListener_1 = require("./gitListener");
const cameraMonitor_1 = require("./cameraMonitor");
const jiraPicker_1 = require("./jiraPicker");
const statusBarSummary_1 = require("./statusBarSummary");
const transparencyCenter_1 = require("./transparencyCenter");
exports.logger = vscode.window.createOutputChannel('DevHouse');
function logTrackingControls() {
    const config = vscode.workspace.getConfiguration('devintel');
    const telemetryEnabled = config.get('telemetryEnabled', true);
    const presenceEnabled = config.get('presenceEnabled', true);
    const backgroundEnabled = config.get('backgroundMonitoringEnabled', true);
    const statusBarEnabled = config.get('showStatusBarSummary', true);
    const uploadConfigured = Boolean(config.get('supabaseUrl', '') && config.get('supabaseKey', ''));
    exports.logger.appendLine(`[CONFIG] telemetry=${telemetryEnabled ? 'on' : 'off'} presence=${presenceEnabled ? 'on' : 'off'} background=${backgroundEnabled ? 'on' : 'off'} statusbar=${statusBarEnabled ? 'on' : 'off'} uploadConfig=${uploadConfigured ? 'ready' : 'missing'}`);
}
async function activate(context) {
    exports.logger.appendLine('DevHouse extension active.');
    // Initialize core modules
    const aggregator = new signalAggregator_1.SignalAggregator();
    const config = vscode.workspace.getConfiguration('devintel');
    // SECURITY: Use SecretStorage for Supabase credentials
    let supabaseUrl = await context.secrets.get('devintel.supabaseUrl') || '';
    let supabaseKey = await context.secrets.get('devintel.supabaseKey') || '';
    // Migration: Check if credentials are in workspace settings and migrate them
    const urlFromConfig = config.get('supabaseUrl', '');
    const keyFromConfig = config.get('supabaseKey', '');
    if (urlFromConfig && !supabaseUrl) {
        await context.secrets.store('devintel.supabaseUrl', urlFromConfig);
        supabaseUrl = urlFromConfig;
        exports.logger.appendLine('[SECURITY] Migrated Supabase URL from settings to secure storage.');
        void vscode.window.showWarningMessage('DevHouse has migrated your Supabase URL to secure storage. Please remove it from settings.', 'Open Settings').then(selection => {
            if (selection === 'Open Settings') {
                void vscode.commands.executeCommand('workbench.action.openSettings', 'devintel.supabaseUrl');
            }
        });
    }
    if (keyFromConfig && !supabaseKey) {
        await context.secrets.store('devintel.supabaseKey', keyFromConfig);
        supabaseKey = keyFromConfig;
        exports.logger.appendLine('[SECURITY] Migrated Supabase API Key from settings to secure storage.');
        void vscode.window.showWarningMessage('DevHouse has migrated your Supabase API Key to secure storage. Please remove it from settings immediately!', 'Open Settings').then(selection => {
            if (selection === 'Open Settings') {
                void vscode.commands.executeCommand('workbench.action.openSettings', 'devintel.supabaseKey');
            }
        });
    }
    const telemetryEnabled = config.get('telemetryEnabled', true);
    const presenceEnabled = config.get('presenceEnabled', true);
    const backgroundEnabled = config.get('backgroundMonitoringEnabled', true);
    const uploadConfigured = Boolean(supabaseUrl && supabaseKey);
    const webhookSender = new webhookSender_1.WebhookSender(supabaseUrl, supabaseKey);
    if (!uploadConfigured) {
        exports.logger.appendLine('[CONFIG] Supabase settings are missing. DevHouse stays local-only until upload and Jira sync are configured.');
        exports.logger.appendLine('[CONFIG] Use "DevHouse: Configure Supabase Credentials" to set up secure upload access.');
    }
    else {
        exports.logger.appendLine('[CONFIG] Supabase settings detected. DevHouse can prepare commit uploads when telemetry upload is enabled.');
    }
    exports.logger.appendLine('[CONFIG] Nothing uploads continuously. Commit data is only prepared when a commit is detected and telemetry upload is enabled.');
    logTrackingControls();
    const activityMonitor = new activityMonitor_1.ActivityMonitor(aggregator);
    activityMonitor.start();
    // SECURITY: Pass context for camera consent management
    const cameraMonitor = new cameraMonitor_1.CameraMonitor(context.globalState, context.workspaceState);
    const backgroundMonitor = new backgroundMonitor_1.BackgroundMonitor(context.globalState);
    const jiraPicker = new jiraPicker_1.JiraPicker(context);
    setTimeout(() => {
        jiraPicker.fetchAndPrompt();
    }, 1000); // Small delay to let git warm up
    const gitListener = new gitListener_1.GitListener(aggregator, activityMonitor, webhookSender, cameraMonitor, backgroundMonitor, jiraPicker);
    await gitListener.initialize();
    const transparencyCenter = new transparencyCenter_1.TransparencyCenter(aggregator, activityMonitor, cameraMonitor, backgroundMonitor, jiraPicker, gitListener);
    const statusBarSummary = new statusBarSummary_1.StatusBarSummary(aggregator, cameraMonitor, backgroundMonitor, jiraPicker, gitListener);
    const selectJiraCommand = vscode.commands.registerCommand('devhouse.selectJiraIssue', async () => {
        await jiraPicker.showPicker();
        statusBarSummary.refresh();
    });
    const showTransparencyCommand = vscode.commands.registerCommand('devhouse.showTransparencyCenter', async () => {
        await transparencyCenter.showTransparencyOverview();
        statusBarSummary.refresh();
    });
    const showSessionSummaryCommand = vscode.commands.registerCommand('devhouse.showSessionSummary', async () => {
        await transparencyCenter.showSessionSummary();
        statusBarSummary.refresh();
    });
    const showDataCollectionStatusCommand = vscode.commands.registerCommand('devhouse.showDataCollectionStatus', async () => {
        await transparencyCenter.showDataCollectionStatus();
        statusBarSummary.refresh();
    });
    const showActiveIssueCommand = vscode.commands.registerCommand('devhouse.showActiveIssue', async () => {
        await transparencyCenter.showActiveIssue();
        statusBarSummary.refresh();
    });
    const resetSessionCommand = vscode.commands.registerCommand('devhouse.resetSessionState', async () => {
        await transparencyCenter.resetSessionState();
        statusBarSummary.refresh();
    });
    const manageTrackingSettingsCommand = vscode.commands.registerCommand('devhouse.manageTrackingSettings', async () => {
        await transparencyCenter.manageTrackingSettings();
        statusBarSummary.refresh();
    });
    const openSettingsCommand = vscode.commands.registerCommand('devhouse.openDevHouseSettings', async () => {
        await vscode.commands.executeCommand('workbench.action.openSettings', 'devintel');
        statusBarSummary.refresh();
    });
    const configureCredentialsCommand = vscode.commands.registerCommand('devhouse.configureSupabaseCredentials', async () => {
        await configureSupabaseCredentials(context);
        statusBarSummary.refresh();
    });
    const configChangeLog = vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration('devintel')) {
            logTrackingControls();
        }
    });
    exports.logger.appendLine('Use "DevHouse: Show Data Collection Status" for a quick trust and upload readiness check.');
    void maybeShowStartupGuidance(context, {
        telemetryEnabled,
        uploadConfigured,
        presenceEnabled,
        backgroundEnabled
    });
    context.subscriptions.push(activityMonitor, gitListener, cameraMonitor, backgroundMonitor, jiraPicker, statusBarSummary, showTransparencyCommand, showSessionSummaryCommand, showDataCollectionStatusCommand, showActiveIssueCommand, resetSessionCommand, manageTrackingSettingsCommand, openSettingsCommand, selectJiraCommand, configureCredentialsCommand, configChangeLog);
}
function deactivate() {
    // Clean up
}
async function configureSupabaseCredentials(context) {
    const urlInput = await vscode.window.showInputBox({
        prompt: 'Enter your Supabase Project URL',
        placeHolder: 'https://your-project.supabase.co',
        ignoreFocusOut: true,
        validateInput: (value) => {
            if (!value) {
                return null; // Allow empty to clear
            }
            if (!value.startsWith('https://') || !value.includes('supabase.co')) {
                return 'Please enter a valid Supabase URL (https://xxx.supabase.co)';
            }
            return null;
        }
    });
    if (urlInput === undefined) {
        return; // User cancelled
    }
    if (!urlInput) {
        await context.secrets.delete('devintel.supabaseUrl');
        exports.logger.appendLine('[CONFIG] Supabase URL cleared from secure storage.');
        void vscode.window.showInformationMessage('Supabase URL removed. DevHouse will run in local-only mode.');
        return;
    }
    const keyInput = await vscode.window.showInputBox({
        prompt: 'Enter your Supabase API Key (anon/public key)',
        placeHolder: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        password: true,
        ignoreFocusOut: true,
        validateInput: (value) => {
            if (!value) {
                return 'API Key is required when URL is provided';
            }
            if (value.length < 20) {
                return 'API Key seems too short. Please check your Supabase settings.';
            }
            return null;
        }
    });
    if (keyInput === undefined) {
        return; // User cancelled
    }
    await context.secrets.store('devintel.supabaseUrl', urlInput);
    await context.secrets.store('devintel.supabaseKey', keyInput);
    exports.logger.appendLine('[CONFIG] Supabase credentials securely stored.');
    const restart = await vscode.window.showInformationMessage('Supabase credentials saved securely. Reload the window to apply changes.', 'Reload Window', 'Later');
    if (restart === 'Reload Window') {
        await vscode.commands.executeCommand('workbench.action.reloadWindow');
    }
}
async function maybeShowStartupGuidance(context, state) {
    const guidanceKey = 'devhouse.startupGuidanceShown';
    const alreadyShown = context.workspaceState.get(guidanceKey, false);
    if (alreadyShown) {
        return;
    }
    const missingSignals = [
        !state.presenceEnabled ? 'presence summaries' : null,
        !state.backgroundEnabled ? 'background summaries' : null
    ].filter(Boolean);
    await context.workspaceState.update(guidanceKey, true);
    const issues = [];
    if (!state.telemetryEnabled) {
        issues.push('telemetry upload is disabled, so commit data stays local-only');
    }
    if (!state.uploadConfigured) {
        issues.push('Supabase settings are missing, so uploads and Jira sync stay unavailable');
    }
    if (missingSignals.length) {
        issues.push(`optional signals disabled: ${missingSignals.join(', ')}`);
    }
    if (!issues.length) {
        return;
    }
    const message = [
        'DevHouse is starting in a limited mode because:',
        ...issues.map((entry, index) => `${index + 1}. ${entry}`),
        '',
        'Local tracking still works. Once the missing configuration is resolved, upload-ready and issue-linking features will resume.'
    ].join('\n');
    const selection = await vscode.window.showInformationMessage(message, 'Configure Credentials', 'Open Settings', 'Show Data Status', 'Continue');
    if (selection === 'Configure Credentials') {
        await vscode.commands.executeCommand('devhouse.configureSupabaseCredentials');
        return;
    }
    if (selection === 'Open Settings') {
        await vscode.commands.executeCommand('workbench.action.openSettings', 'devintel');
        return;
    }
    if (selection === 'Show Data Status') {
        await vscode.commands.executeCommand('devhouse.showDataCollectionStatus');
    }
}
//# sourceMappingURL=extension.js.map