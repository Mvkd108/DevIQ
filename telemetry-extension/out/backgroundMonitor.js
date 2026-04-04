"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.BackgroundMonitor = void 0;
const cp = require("child_process");
const os = require("os");
const vscode = require("vscode");
const extension_1 = require("./extension");
const APP_WHITELIST = {
    'chrome.exe': 'Google Chrome',
    'chrome': 'Google Chrome',
    'firefox.exe': 'Mozilla Firefox',
    'firefox': 'Mozilla Firefox',
    'msedge.exe': 'Microsoft Edge',
    'msedge': 'Microsoft Edge',
    'code.exe': 'Visual Studio Code',
    'code': 'Visual Studio Code',
    'slack.exe': 'Slack',
    'slack': 'Slack',
    'teams.exe': 'Microsoft Teams',
    'teams': 'Microsoft Teams',
    'discord.exe': 'Discord',
    'discord': 'Discord',
    'spotify.exe': 'Spotify',
    'spotify': 'Spotify',
    'zoom.exe': 'Zoom',
    'zoom.us': 'Zoom',
    'postman.exe': 'Postman',
    'postman': 'Postman',
    'figma.exe': 'Figma',
    'figma': 'Figma',
    'notion.exe': 'Notion',
    'notion': 'Notion',
    'obs64.exe': 'OBS Studio',
    'obs': 'OBS Studio'
};
class BackgroundMonitor {
    state;
    trackedApps = new Map();
    intervalId;
    lastScanAt = null;
    monitoringActive = false;
    lastErrorKey = null;
    constructor(state) {
        this.state = state;
        const savedApps = this.state.get('devintel.backgroundApps', {});
        for (const [key, value] of Object.entries(savedApps)) {
            this.trackedApps.set(key, value);
        }
        this.start();
        vscode.workspace.onDidChangeConfiguration((e) => {
            if (e.affectsConfiguration('devintel.telemetryEnabled') || e.affectsConfiguration('devintel.backgroundMonitoringEnabled')) {
                this.start();
            }
        });
    }
    start() {
        const config = vscode.workspace.getConfiguration('devintel');
        const enabled = config.get('telemetryEnabled', true);
        const backgroundEnabled = config.get('backgroundMonitoringEnabled', true);
        if (!enabled || !backgroundEnabled) {
            this.stop();
            if (this.monitoringActive) {
                extension_1.logger.appendLine('[BACKGROUND APP] Local background summaries paused by settings.');
                this.monitoringActive = false;
            }
            return;
        }
        if (!this.intervalId) {
            this.intervalId = setInterval(() => {
                this.checkApps();
            }, 60000);
            if (!this.monitoringActive) {
                extension_1.logger.appendLine('[BACKGROUND APP] Local background summaries enabled for whitelisted apps.');
                this.monitoringActive = true;
            }
            this.checkApps();
        }
    }
    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = undefined;
        }
    }
    checkApps() {
        const isWindows = os.platform() === 'win32';
        const cmd = isWindows ? 'tasklist /FO CSV /NH' : 'ps aux';
        cp.exec(cmd, { maxBuffer: 1024 * 1024 * 5 }, (error, stdout) => {
            if (error) {
                this.logErrorOnce('scan-error', `[BACKGROUND APP] Could not inspect local background apps: ${error.message}`);
                return;
            }
            this.clearError();
            const now = Date.now();
            this.lastScanAt = now;
            const lines = stdout.split('\n');
            const seenInThisCheck = new Set();
            for (const line of lines) {
                let textToMatch = '';
                if (isWindows) {
                    const match = line.match(/^"([^"]+)"/);
                    if (match) {
                        textToMatch = match[1].toLowerCase();
                    }
                }
                else {
                    const parts = line.trim().split(/\s+/);
                    if (parts.length > 10) {
                        textToMatch = parts.slice(10).join(' ').toLowerCase();
                    }
                }
                if (!textToMatch) {
                    continue;
                }
                let matchedAppName;
                let matchedProcessName;
                for (const [key, appName] of Object.entries(APP_WHITELIST)) {
                    if ((isWindows && textToMatch === key) || (!isWindows && textToMatch.includes(key))) {
                        matchedAppName = appName;
                        matchedProcessName = key;
                        break;
                    }
                }
                if (matchedAppName && matchedProcessName && !seenInThisCheck.has(matchedProcessName)) {
                    seenInThisCheck.add(matchedProcessName);
                    const existing = this.trackedApps.get(matchedProcessName);
                    if (existing) {
                        existing.last_seen = now;
                    }
                    else {
                        this.trackedApps.set(matchedProcessName, {
                            app_name: matchedAppName,
                            process_name: matchedProcessName,
                            first_seen: now,
                            last_seen: now
                        });
                    }
                }
            }
            this.saveState();
        });
    }
    saveState() {
        const objToSave = {};
        for (const [key, value] of this.trackedApps.entries()) {
            objToSave[key] = value;
        }
        this.state.update('devintel.backgroundApps', objToSave);
    }
    getTrackedApps() {
        const result = [];
        for (const app of this.trackedApps.values()) {
            const durationSecs = Math.floor((app.last_seen - app.first_seen) / 1000);
            result.push({
                app_name: app.app_name,
                process_name: app.process_name,
                first_seen: new Date(app.first_seen).toISOString(),
                last_seen: new Date(app.last_seen).toISOString(),
                duration_seconds: durationSecs
            });
        }
        return result.sort((left, right) => right.duration_seconds - left.duration_seconds);
    }
    isEnabled() {
        const config = vscode.workspace.getConfiguration('devintel');
        return config.get('telemetryEnabled', true) && config.get('backgroundMonitoringEnabled', true);
    }
    getWhitelistedApps() {
        return Array.from(new Set(Object.values(APP_WHITELIST))).sort((left, right) => left.localeCompare(right));
    }
    getStatus() {
        return {
            enabled: this.isEnabled(),
            lastScanAt: this.lastScanAt ? new Date(this.lastScanAt).toISOString() : null,
            trackedApps: this.getTrackedApps(),
            whitelistedApps: this.getWhitelistedApps()
        };
    }
    resetSession() {
        this.trackedApps.clear();
        this.lastScanAt = null;
        this.lastErrorKey = null;
        this.saveState();
        extension_1.logger.appendLine('[BACKGROUND APP] Local background summary session was reset.');
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
exports.BackgroundMonitor = BackgroundMonitor;
//# sourceMappingURL=backgroundMonitor.js.map