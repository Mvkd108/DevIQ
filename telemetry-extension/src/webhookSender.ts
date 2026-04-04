import { SupaBaseEvent } from './types';
import { logger } from './extension';

export class WebhookSender {
    private supabaseUrl: string;
    private supabaseKey: string;

    constructor(supabaseUrl: string = '', supabaseKey: string = '') {
        this.supabaseUrl = supabaseUrl;
        this.supabaseKey = supabaseKey;
    }

    public updateConfig(supabaseUrl: string, supabaseKey: string): void {
        this.supabaseUrl = supabaseUrl;
        this.supabaseKey = supabaseKey;
    }

    private getBaseUrl(): string {
        return `${this.supabaseUrl.replace(/\/$/, '')}/rest/v1/extension_events`;
    }

    private getHeaders(extraHeaders: Record<string, string> = {}): Record<string, string> {
        return {
            'Content-Type': 'application/json',
            'apikey': this.supabaseKey,
            'Authorization': `Bearer ${this.supabaseKey}`,
            ...extraHeaders
        };
    }

    public async sendToSupabase(payload: SupaBaseEvent): Promise<boolean> {
        if (!this.supabaseUrl || !this.supabaseKey) {
            logger.appendLine('[SYNC] Upload skipped because Supabase settings are incomplete.');
            return false;
        }

        try {
            const deleted = await this.deleteEventByIdentity(payload.commit_id, payload.developer_id, payload.repository_name);
            if (!deleted) {
                return false;
            }

            const url = this.getBaseUrl();
            const headers = this.getHeaders({ 'Prefer': 'return=minimal' });
            const jsonBody = JSON.stringify(payload);

            const response = await fetch(url, {
                method: 'POST',
                headers,
                body: jsonBody
            });

            if (!response.ok) {
                if (response.status === 409) {
                    logger.appendLine(`[SYNC] Commit ${payload.commit_id.substring(0, 7)} is already mirrored remotely.`);
                    return true;
                }
                const errorText = await response.text();
                logger.appendLine(`[SYNC] Upload failed with ${response.status} ${response.statusText}: ${errorText}`);
                return false;
            }

            logger.appendLine(`[SYNC] Uploaded commit event ${payload.commit_id.substring(0, 7)}.`);
            return true;
        } catch (error) {
            logger.appendLine(`[SYNC] Upload failed: ${error}`);
            return false;
        }
    }

    public async fetchRemoteCommitIds(developerId: string, repositoryName: string): Promise<string[]> {
        if (!this.supabaseUrl || !this.supabaseKey) {
            return [];
        }

        const params = new URLSearchParams({
            select: 'commit_id',
            developer_id: `eq.${developerId}`,
            repository_name: `eq.${repositoryName}`,
            limit: '5000'
        });
        const url = `${this.getBaseUrl()}?${params.toString()}`;

        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: this.getHeaders()
            });

            if (!response.ok) {
                const errorText = await response.text();
                logger.appendLine(`[SYNC] Could not fetch remote commit ids: ${response.status} ${response.statusText} ${errorText}`);
                return [];
            }

            const rows = await response.json() as Array<{ commit_id?: string }>;
            return rows.map(row => row.commit_id).filter((commitId): commitId is string => Boolean(commitId));
        } catch (error) {
            logger.appendLine(`[SYNC] Could not fetch remote commit ids: ${error}`);
            return [];
        }
    }

    public async deleteEventByIdentity(commitId: string, developerId: string, repositoryName: string): Promise<boolean> {
        if (!this.supabaseUrl || !this.supabaseKey) {
            return false;
        }

        const params = new URLSearchParams({
            commit_id: `eq.${commitId}`,
            developer_id: `eq.${developerId}`,
            repository_name: `eq.${repositoryName}`
        });
        const url = `${this.getBaseUrl()}?${params.toString()}`;

        try {
            const response = await fetch(url, {
                method: 'DELETE',
                headers: this.getHeaders({ 'Prefer': 'return=minimal' })
            });

            if (!response.ok) {
                const errorText = await response.text();
                logger.appendLine(`[SYNC] Could not clear an older remote copy of ${commitId.substring(0, 7)}: ${response.status} ${response.statusText} ${errorText}`);
                return false;
            }

            return true;
        } catch (error) {
            logger.appendLine(`[SYNC] Could not clear an older remote copy of ${commitId.substring(0, 7)}: ${error}`);
            return false;
        }
    }
}
