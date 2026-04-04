"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CameraMonitor = void 0;
const vscode = require("vscode");
const extension_1 = require("./extension");
const cp = require("child_process");
const path = require("path");
const fs = require("fs");
class CameraMonitor {
    state;
    workspaceState;
    checks = [];
    sessionStart;
    intervalId;
    scriptPath;
    lastCheckAt = null;
    lastCheckResult = null;
    monitoringActive = false;
    lastErrorKey = null;
    consentChecked = false;
    constructor(state, workspaceState) {
        this.state = state;
        this.workspaceState = workspaceState;
        this.scriptPath = this.resolveScriptPath();
        // Restore state
        this.checks = this.state.get('devintel.presence.checks', []);
        this.sessionStart = this.state.get('devintel.presence.sessionStart', Date.now());
        if (this.sessionStart === 0 || this.checks.length === 0) {
            this.sessionStart = Date.now();
            this.saveState();
        }
        // SECURITY: Don't start automatically - wait for consent check
        void this.checkConsentAndStart();
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('devintel.telemetryEnabled') || e.affectsConfiguration('devintel.presenceEnabled')) {
                void this.checkConsentAndStart();
            }
        });
    }
    async checkConsentAndStart() {
        const config = vscode.workspace.getConfiguration('devintel');
        const enabled = config.get('telemetryEnabled', true);
        const presenceEnabled = config.get('presenceEnabled', false);
        if (!enabled || !presenceEnabled) {
            this.stop();
            if (this.monitoringActive) {
                extension_1.logger.appendLine('[PRESENCE] Local presence summaries paused by settings.');
                this.monitoringActive = false;
            }
            return;
        }
        // SECURITY: Check for explicit user consent before accessing camera
        const consentKey = 'devintel.cameraConsent';
        const hasConsent = this.workspaceState.get(consentKey, false);
        if (!hasConsent && !this.consentChecked) {
            this.consentChecked = true;
            const result = await vscode.window.showWarningMessage('DevHouse Camera Monitoring Consent', {
                modal: true,
                detail: [
                    'DevHouse wants to use your camera for presence detection.',
                    '',
                    'What data is collected:',
                    '• Periodic checks (every 45 seconds) to detect if someone is present',
                    '• Only summary statistics (% present, check counts) are stored',
                    '• Raw camera frames are NEVER saved or uploaded',
                    '',
                    'Why this is collected:',
                    '• To provide accurate work session summaries',
                    '• To help you understand your actual coding time',
                    '',
                    'Your privacy:',
                    '• All processing happens locally on your machine',
                    '• You can disable this anytime in settings (devintel.presenceEnabled)',
                    '• You can view all collected data via "DevHouse: Show Data Collection Status"',
                    '',
                    'Camera monitoring will NOT start unless you click "Allow".'
                ].join('\n')
            }, 'Allow', 'Deny');
            if (result === 'Allow') {
                await this.workspaceState.update(consentKey, true);
                extension_1.logger.appendLine('[PRESENCE] Camera access consent granted by user.');
                this.start();
            }
            else {
                extension_1.logger.appendLine('[PRESENCE] Camera access consent denied by user. Presence monitoring disabled.');
                await config.update('presenceEnabled', false, vscode.ConfigurationTarget.Workspace);
                void vscode.window.showInformationMessage('Camera monitoring disabled. You can re-enable it later in DevHouse settings.', 'Open Settings').then(selection => {
                    if (selection === 'Open Settings') {
                        void vscode.commands.executeCommand('workbench.action.openSettings', 'devintel.presenceEnabled');
                    }
                });
            }
        }
        else if (hasConsent) {
            this.start();
        }
    }
    start() {
        const config = vscode.workspace.getConfiguration('devintel');
        const enabled = config.get('telemetryEnabled', true);
        const presenceEnabled = config.get('presenceEnabled', false);
        if (!enabled || !presenceEnabled) {
            this.stop();
            if (this.monitoringActive) {
                extension_1.logger.appendLine('[PRESENCE] Local presence summaries paused by settings.');
                this.monitoringActive = false;
            }
            return;
        }
        if (!this.intervalId) {
            this.intervalId = setInterval(() => {
                this.checkPresence();
            }, 45000);
            if (!this.monitoringActive) {
                extension_1.logger.appendLine('[PRESENCE] Local presence summaries enabled.');
                this.monitoringActive = true;
            }
            // Initial check immediately
            this.checkPresence();
        }
    }
    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = undefined;
        }
    }
    checkPresence() {
        if (!fs.existsSync(this.scriptPath)) {
            this.logErrorOnce('missing-script', `[PRESENCE] Face detection helper was not found at ${this.scriptPath}. Presence summaries will mark checks as not detected.`);
            this.recordCheck(0);
            return;
        }
        this.runPythonScript([...this.getPythonCommandCandidates()], this.scriptPath);
    }
    resolveScriptPath() {
        const candidates = [
            path.join(__dirname, '..', 'src', 'detect_face.py'),
            path.join(__dirname, 'detect_face.py')
        ];
        for (const candidate of candidates) {
            if (fs.existsSync(candidate)) {
                return candidate;
            }
        }
        return candidates[0];
    }
    getPythonCommandCandidates() {
        const config = vscode.workspace.getConfiguration('devintel');
        const configured = (config.get('pythonCommand', '') || '').trim();
        const isWindows = process.platform === 'win32';
        const candidates = [configured, isWindows ? 'python' : 'python3', 'python', 'py'].filter(Boolean);
        return [...new Set(candidates)];
    }
    runPythonScript(commands, scriptPath) {
        const command = commands.shift();
        if (!command) {
            this.logErrorOnce('missing-python', '[PRESENCE] No working Python interpreter was available for local presence summaries.');
            this.recordCheck(0);
            return;
        }
        cp.execFile(command, [scriptPath], { windowsHide: true }, (error, stdout, stderr) => {
            if (error) {
                const detail = stderr.trim() ? ` ${stderr.trim()}` : '';
                this.logErrorOnce(`python-failed-${command}`, `[PRESENCE] Presence helper could not run with "${command}".${detail}`.trim());
                this.runPythonScript(commands, scriptPath);
                return;
            }
            const result = stdout.trim();
            if (result === '1') {
                this.clearError();
                this.recordCheck(1);
            }
            else if (result === '0') {
                this.clearError();
                this.recordCheck(0);
            }
            else {
                this.logErrorOnce(`unexpected-output-${result}`, `[PRESENCE] Presence helper returned an unexpected value (${result || '<empty>'}).`);
                this.recordCheck(0);
            }
        });
    }
    recordCheck(value) {
        this.checks.push(value);
        this.lastCheckAt = Date.now();
        this.lastCheckResult = value;
        this.saveState();
    }
    saveState() {
        this.state.update('devintel.presence.checks', this.checks);
        this.state.update('devintel.presence.sessionStart', this.sessionStart);
    }
    getPresenceData() {
        const total = this.checks.length;
        const present = this.checks.reduce((a, b) => a + b, 0);
        const pct = total === 0 ? 0 : (present / total) * 100;
        const durationSecs = Math.floor((Date.now() - this.sessionStart) / 1000);
        return {
            attendance_pct: Number(pct.toFixed(2)),
            total_checks: total,
            present_checks: present,
            session_duration_seconds: durationSecs,
            session_start: new Date(this.sessionStart).toISOString()
        };
    }
    triggerPresenceCheck() {
        this.checkPresence();
    }
    isEnabled() {
        const config = vscode.workspace.getConfiguration('devintel');
        return config.get('telemetryEnabled', true) && config.get('presenceEnabled', false);
    }
    getStatus() {
        const data = this.getPresenceData();
        return {
            enabled: this.isEnabled(),
            scriptPath: this.scriptPath,
            lastCheckAt: this.lastCheckAt ? new Date(this.lastCheckAt).toISOString() : null,
            lastCheckResult: this.lastCheckResult === null ? null : this.lastCheckResult === 1,
            ...data
        };
    }
    resetSession() {
        this.checks = [];
        this.sessionStart = Date.now();
        this.lastCheckAt = null;
        this.lastCheckResult = null;
        this.lastErrorKey = null;
        this.consentChecked = false;
        this.saveState();
        extension_1.logger.appendLine('[PRESENCE] Local presence session was reset.');
    }
    dispose() {
        this.stop();
    }
    logErrorOnce(key, message) {
        if (this.lastErrorKey === key) {
            return;
        }
        this.lastErrorKey = key;
        extension_1.logger.appendLine(message);
    }
    clearError() {
        this.lastErrorKey = null;
    }
}
exports.CameraMonitor = CameraMonitor;
//# sourceMappingURL=cameraMonitor.js.map