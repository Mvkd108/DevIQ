"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.WebhookSender = void 0;
const extension_1 = require("./extension");
class WebhookSender {
    supabaseUrl;
    supabaseKey;
    constructor(supabaseUrl = '', supabaseKey = '') {
        this.supabaseUrl = supabaseUrl;
        this.supabaseKey = supabaseKey;
    }
    updateConfig(supabaseUrl, supabaseKey) {
        this.supabaseUrl = supabaseUrl;
        this.supabaseKey = supabaseKey;
    }
    getBaseUrl() {
        return `${this.supabaseUrl.replace(/\/$/, '')}/rest/v1/extension_events`;
    }
    getHeaders(extraHeaders = {}) {
        return {
            'Content-Type': 'application/json',
            'apikey': this.supabaseKey,
            'Authorization': `Bearer ${this.supabaseKey}`,
            ...extraHeaders
        };
    }
    async sendToSupabase(payload) {
        if (!this.supabaseUrl || !this.supabaseKey) {
            extension_1.logger.appendLine('[SYNC] Upload skipped because Supabase settings are incomplete.');
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
                    extension_1.logger.appendLine(`[SYNC] Commit ${payload.commit_id.substring(0, 7)} is already mirrored remotely.`);
                    return true;
                }
                const errorText = await response.text();
                extension_1.logger.appendLine(`[SYNC] Upload failed with ${response.status} ${response.statusText}: ${errorText}`);
                return false;
            }
            extension_1.logger.appendLine(`[SYNC] Uploaded commit event ${payload.commit_id.substring(0, 7)}.`);
            return true;
        }
        catch (error) {
            extension_1.logger.appendLine(`[SYNC] Upload failed: ${error}`);
            return false;
        }
    }
    async fetchRemoteCommitIds(developerId, repositoryName) {
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
                extension_1.logger.appendLine(`[SYNC] Could not fetch remote commit ids: ${response.status} ${response.statusText} ${errorText}`);
                return [];
            }
            const rows = await response.json();
            return rows.map(row => row.commit_id).filter((commitId) => Boolean(commitId));
        }
        catch (error) {
            extension_1.logger.appendLine(`[SYNC] Could not fetch remote commit ids: ${error}`);
            return [];
        }
    }
    async deleteEventByIdentity(commitId, developerId, repositoryName) {
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
                extension_1.logger.appendLine(`[SYNC] Could not clear an older remote copy of ${commitId.substring(0, 7)}: ${response.status} ${response.statusText} ${errorText}`);
                return false;
            }
            return true;
        }
        catch (error) {
            extension_1.logger.appendLine(`[SYNC] Could not clear an older remote copy of ${commitId.substring(0, 7)}: ${error}`);
            return false;
        }
    }
}
exports.WebhookSender = WebhookSender;
//# sourceMappingURL=webhookSender.js.map