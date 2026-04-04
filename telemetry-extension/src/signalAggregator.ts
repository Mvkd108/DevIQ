import { SignalSession } from './types';

export class SignalAggregator {
    private static readonly IDLE_THRESHOLD_MS = 60_000;
    private session!: SignalSession;
    private sessionStartTime!: number;
    private lastInteractionTime!: number;
    private accumulatedIdleMs!: number;
    private accumulatedFocusMs!: number;
    private focusedSince: number | null = null;
    private isWindowFocused = true;

    constructor() {
        this.resetSession();
    }

    public resetSession(): void {
        this.sessionStartTime = Date.now();
        this.session = {
            session_id: `sess_${Date.now()}`,
            files_opened: 0,
            files_modified: 0,
            lines_added: 0,
            lines_deleted: 0,
            editing_duration_minutes: 0,
            refactor_events: 0,
            idle_minutes: 0,
            focus_ratio: 1,
            debug_session_count: 0
        };
        this.lastInteractionTime = this.sessionStartTime;
        this.accumulatedIdleMs = 0;
        this.accumulatedFocusMs = 0;
        this.focusedSince = this.sessionStartTime;
        this.isWindowFocused = true;
    }

    public addFilesOpened(count: number = 1): void {
        this.session.files_opened += count;
    }

    public addFileModified(): void {
        this.session.files_modified += 1;
    }

    public addLinesChanged(added: number, deleted: number): void {
        if (added > 0 || deleted > 0) {
            this.session.lines_added += added;
            this.session.lines_deleted += deleted;
            
            // Heuristic for refactor: many lines deleted and added at once
            if (added > 20 && deleted > 20) {
                this.session.refactor_events += 1;
            }
        }
    }

    public recordInteraction(timestamp: number = Date.now()): void {
        const gap = timestamp - this.lastInteractionTime;
        if (gap > SignalAggregator.IDLE_THRESHOLD_MS) {
            this.accumulatedIdleMs += gap - SignalAggregator.IDLE_THRESHOLD_MS;
        }
        this.lastInteractionTime = timestamp;
    }

    public setWindowFocus(focused: boolean, timestamp: number = Date.now()): void {
        if (focused === this.isWindowFocused) {
            return;
        }

        if (this.isWindowFocused && this.focusedSince !== null) {
            this.accumulatedFocusMs += Math.max(0, timestamp - this.focusedSince);
            this.focusedSince = null;
        }

        this.isWindowFocused = focused;
        if (focused) {
            this.focusedSince = timestamp;
            this.recordInteraction(timestamp);
        }
    }

    public addDebugSession(): void {
        this.session.debug_session_count += 1;
        this.recordInteraction();
    }
    
    public updateDuration(): void {
        const now = Date.now();
        const sessionDurationMs = Math.max(0, now - this.sessionStartTime);
        const trailingIdleMs = Math.max(0, now - this.lastInteractionTime - SignalAggregator.IDLE_THRESHOLD_MS);
        const idleMs = this.accumulatedIdleMs + trailingIdleMs;
        const focusedMs = this.accumulatedFocusMs + (
            this.isWindowFocused && this.focusedSince !== null ? Math.max(0, now - this.focusedSince) : 0
        );
        const activeMs = Math.max(0, sessionDurationMs - idleMs);

        this.session.editing_duration_minutes = Math.floor(activeMs / 60000);
        this.session.idle_minutes = Math.floor(idleMs / 60000);
        this.session.focus_ratio = sessionDurationMs === 0 ? 0 : Number((focusedMs / sessionDurationMs).toFixed(3));
    }

    public getSession(): SignalSession {
        this.updateDuration();
        return this.session;
    }
}
