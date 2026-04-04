export interface SignalSession {
    session_id: string;
    files_opened: number;
    files_modified: number;
    lines_added: number;
    lines_deleted: number;
    editing_duration_minutes: number;
    refactor_events: number;
    idle_minutes: number;
    focus_ratio: number;
    debug_session_count: number;
}

export interface CommitFile {
    file_path: string;
    file_extension: string;
    change_type: string;
    additions: number;
    deletions: number;
    language: string;
    patch: string;
    module: string;
    directory: string;
    commit_id: string;
}

export interface PresenceData {
    attendance_pct: number;
    total_checks: number;
    present_checks: number;
    session_duration_seconds: number;
    session_start: string;
}

export interface BackgroundAppSessionEntry {
    app_name: string;
    process_name: string;
    first_seen: string;
    last_seen: string;
    duration_seconds: number;
}

// Supabase schema-aligned event
export interface SupaBaseEvent {
    id?: string;
    event_type: string;
    schema_version: string;
    developer_id: string;
    commit_id: string;
    author: string;
    author_email: string;
    message: string;
    repository_owner: string | null;
    repository_name: string;
    timestamp: string; // ISO format
    branch: string;
    additions: number;
    deletions: number;
    commit_type: string;
    parent_commit_id: string | null;
    commit_category: string;
    commit_message_length: number;
    total_changes: number;
    commit_size: number;
    is_merge_commit: boolean;
    linked_issue: string | null;
    issue_id?: string | null;
    pull_request_number: number | null;
    pr_title: string | null;
    pr_labels: string[];
    files: CommitFile[];
    files_changed_count?: number;
    net_loc?: number;
    diff_patch?: string;
    files_json?: any;
    modules_touched?: string[];
    background_apps?: BackgroundAppSessionEntry[];
    attendance_pct?: number;
    presence_total_checks?: number;
    presence_present_count?: number;
    session_duration_secs?: number;
    session_start?: string;
    active_minutes: number;
    idle_minutes?: number | null;
    focus_ratio?: number | null;
    debug_session_count?: number | null;
}

export interface ExtensionConfig {
    supabaseUrl: string;
    supabaseKey: string;
    developerId: string;
    repositoryName: string;
    telemetryEnabled: boolean;
}

export interface TrackingControls {
    telemetryEnabled: boolean;
    presenceEnabled: boolean;
    backgroundMonitoringEnabled: boolean;
    uploadConfigured: boolean;
    statusBarSummaryEnabled: boolean;
}

export interface PresenceMonitorStatus extends PresenceData {
    enabled: boolean;
    scriptPath: string;
    lastCheckAt: string | null;
    lastCheckResult: boolean | null;
}

export interface BackgroundMonitorStatus {
    enabled: boolean;
    lastScanAt: string | null;
    trackedApps: BackgroundAppSessionEntry[];
    whitelistedApps: string[];
}

export interface NextCommitPreview {
    repositoryName: string;
    repositoryPath: string;
    branch: string;
    changedFiles: string[];
    pendingLocalEventCount: number;
}

export interface UploadBoundaryPreview {
    localOnly: string[];
    uploadedOnCommit: string[];
    optionalWhenEnabled: string[];
    neverUploaded: string[];
}

export type TransparencyAction =
    | 'summary'
    | 'settings'
    | 'issue'
    | 'transparency'
    | 'status'
    | 'localOnly'
    | 'uploadedOnCommit'
    | 'neverUploaded';

export interface TransparencyStatusItem {
    label: string;
    description: string;
    detail: string;
    action: TransparencyAction;
}
