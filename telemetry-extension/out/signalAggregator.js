"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SignalAggregator = void 0;
class SignalAggregator {
    static IDLE_THRESHOLD_MS = 60_000;
    session;
    sessionStartTime;
    lastInteractionTime;
    accumulatedIdleMs;
    accumulatedFocusMs;
    focusedSince = null;
    isWindowFocused = true;
    constructor() {
        this.resetSession();
    }
    resetSession() {
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
    addFilesOpened(count = 1) {
        this.session.files_opened += count;
    }
    addFileModified() {
        this.session.files_modified += 1;
    }
    addLinesChanged(added, deleted) {
        if (added > 0 || deleted > 0) {
            this.session.lines_added += added;
            this.session.lines_deleted += deleted;
            // Heuristic for refactor: many lines deleted and added at once
            if (added > 20 && deleted > 20) {
                this.session.refactor_events += 1;
            }
        }
    }
    recordInteraction(timestamp = Date.now()) {
        const gap = timestamp - this.lastInteractionTime;
        if (gap > SignalAggregator.IDLE_THRESHOLD_MS) {
            this.accumulatedIdleMs += gap - SignalAggregator.IDLE_THRESHOLD_MS;
        }
        this.lastInteractionTime = timestamp;
    }
    setWindowFocus(focused, timestamp = Date.now()) {
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
    addDebugSession() {
        this.session.debug_session_count += 1;
        this.recordInteraction();
    }
    updateDuration() {
        const now = Date.now();
        const sessionDurationMs = Math.max(0, now - this.sessionStartTime);
        const trailingIdleMs = Math.max(0, now - this.lastInteractionTime - SignalAggregator.IDLE_THRESHOLD_MS);
        const idleMs = this.accumulatedIdleMs + trailingIdleMs;
        const focusedMs = this.accumulatedFocusMs + (this.isWindowFocused && this.focusedSince !== null ? Math.max(0, now - this.focusedSince) : 0);
        const activeMs = Math.max(0, sessionDurationMs - idleMs);
        this.session.editing_duration_minutes = Math.floor(activeMs / 60000);
        this.session.idle_minutes = Math.floor(idleMs / 60000);
        this.session.focus_ratio = sessionDurationMs === 0 ? 0 : Number((focusedMs / sessionDurationMs).toFixed(3));
    }
    getSession() {
        this.updateDuration();
        return this.session;
    }
}
exports.SignalAggregator = SignalAggregator;
//# sourceMappingURL=signalAggregator.js.map