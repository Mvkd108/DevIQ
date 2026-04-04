import * as cp from 'child_process';
import * as os from 'os';
import * as vscode from 'vscode';
import { logger } from './extension';
import { BackgroundAppSessionEntry, BackgroundMonitorStatus } from './types';

const APP_WHITELIST: Record<string, string> = {
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

interface BackgroundAppState {
    app_name: string;
    process_name: string;
    first_seen: number;
    last_seen: number;
}

export class BackgroundMonitor implements vscode.Disposable {
    private state: vscode.Memento;
    private trackedApps = new Map<string, BackgroundAppState>();
    private intervalId?: NodeJS.Timeout;
    private lastScanAt: number | null = null;
    private monitoringActive = false;
    private lastErrorKey: string | null = null;

    constructor(state: vscode.Memento) {
        this.state = state;

        const savedApps = this.state.get<Record<string, BackgroundAppState>>('devintel.backgroundApps', {});
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

    private start(): void {
        const config = vscode.workspace.getConfiguration('devintel');
        const enabled = config.get<boolean>('telemetryEnabled', true);
        const backgroundEnabled = config.get<boolean>('backgroundMonitoringEnabled', true);

        if (!enabled || !backgroundEnabled) {
            this.stop();
            if (this.monitoringActive) {
                logger.appendLine('[BACKGROUND APP] Local background summaries paused by settings.');
                this.monitoringActive = false;
            }
            return;
        }

        if (!this.intervalId) {
            this.intervalId = setInterval(() => {
                this.checkApps();
            }, 60000);

            if (!this.monitoringActive) {
                logger.appendLine('[BACKGROUND APP] Local background summaries enabled for whitelisted apps.');
                this.monitoringActive = true;
            }
            this.checkApps();
        }
    }

    private stop(): void {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = undefined;
        }
    }

    private checkApps(): void {
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
            const seenInThisCheck = new Set<string>();

            for (const line of lines) {
                let textToMatch = '';

                if (isWindows) {
                    const match = line.match(/^"([^"]+)"/);
                    if (match) {
                        textToMatch = match[1].toLowerCase();
                    }
                } else {
                    const parts = line.trim().split(/\s+/);
                    if (parts.length > 10) {
                        textToMatch = parts.slice(10).join(' ').toLowerCase();
                    }
                }

                if (!textToMatch) {
                    continue;
                }

                let matchedAppName: string | undefined;
                let matchedProcessName: string | undefined;

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
                    } else {
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

    private saveState(): void {
        const objToSave: Record<string, BackgroundAppState> = {};
        for (const [key, value] of this.trackedApps.entries()) {
            objToSave[key] = value;
        }
        this.state.update('devintel.backgroundApps', objToSave);
    }

    public getTrackedApps(): BackgroundAppSessionEntry[] {
        const result: BackgroundAppSessionEntry[] = [];
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

    public isEnabled(): boolean {
        const config = vscode.workspace.getConfiguration('devintel');
        return config.get<boolean>('telemetryEnabled', true) && config.get<boolean>('backgroundMonitoringEnabled', true);
    }

    public getWhitelistedApps(): string[] {
        return Array.from(new Set(Object.values(APP_WHITELIST))).sort((left, right) => left.localeCompare(right));
    }

    public getStatus(): BackgroundMonitorStatus {
        return {
            enabled: this.isEnabled(),
            lastScanAt: this.lastScanAt ? new Date(this.lastScanAt).toISOString() : null,
            trackedApps: this.getTrackedApps(),
            whitelistedApps: this.getWhitelistedApps()
        };
    }

    public resetSession(): void {
        this.trackedApps.clear();
        this.lastScanAt = null;
        this.lastErrorKey = null;
        this.saveState();
        logger.appendLine('[BACKGROUND APP] Local background summary session was reset.');
    }

    public dispose(): void {
        this.stop();
    }

    private logErrorOnce(key: string, message: string): void {
        if (this.lastErrorKey === key) {
            return;
        }

        this.lastErrorKey = key;
        logger.appendLine(message);
    }

    private clearError(): void {
        this.lastErrorKey = null;
    }
}
