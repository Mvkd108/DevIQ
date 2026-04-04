/**
 * Attribution API Service
 * 
 * Client functions for attribution system API endpoints.
 * All functions return promises and handle errors consistently.
 * 
 * @module services/attributionApi
 */

const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL 
  || import.meta.env?.VITE_API_URL 
  || "http://127.0.0.1:8000";

/**
 * Fetch identity resolution status
 * @returns {Promise<{status: string, stats: Object}>}
 */
export async function fetchIdentityStatus() {
  const response = await fetch(`${API_BASE_URL}/api/identity-resolution/status`);
  if (!response.ok) throw new Error(`Identity status failed: ${response.status}`);
  return response.json();
}

/**
 * Fetch developer ownership information
 * @param {string} developerId - Canonical developer ID
 * @returns {Promise<{developer: Object, ownership: Array}>}
 */
export async function fetchDeveloperOwnership(developerId) {
  const response = await fetch(`${API_BASE_URL}/api/developers/${developerId}/ownership`);
  if (!response.ok) throw new Error(`Developer ownership failed: ${response.status}`);
  return response.json();
}

/**
 * Fetch developer attribution history
 * @param {string} developerId - Canonical developer ID
 * @returns {Promise<{developer_id: string, history: Array}>}
 */
export async function fetchDeveloperAttributionHistory(developerId) {
  const response = await fetch(`${API_BASE_URL}/api/developers/${developerId}/attribution-history`);
  if (!response.ok) throw new Error(`Attribution history failed: ${response.status}`);
  return response.json();
}

/**
 * Fetch manager team attribution rollup
 * @param {string} managerId - Manager ID
 * @returns {Promise<{manager_id: string, rollup: Object}>}
 */
export async function fetchManagerTeamAttribution(managerId) {
  const response = await fetch(`${API_BASE_URL}/api/managers/${managerId}/team-attribution`);
  if (!response.ok) throw new Error(`Team attribution failed: ${response.status}`);
  return response.json();
}

/**
 * Fetch manager team dependencies
 * @param {string} managerId - Manager ID
 * @returns {Promise<{manager_id: string, team_dependencies: Array}>}
 */
export async function fetchManagerTeamDependencies(managerId) {
  const response = await fetch(`${API_BASE_URL}/api/managers/${managerId}/team-dependencies`);
  if (!response.ok) throw new Error(`Team dependencies failed: ${response.status}`);
  return response.json();
}

/**
 * Fetch repository dependency graph
 * @param {string} repoName - Repository name
 * @returns {Promise<{repository: string, nodes: Array, edges: Array}>}
 */
export async function fetchRepositoryDependencyGraph(repoName) {
  const response = await fetch(`${API_BASE_URL}/api/repositories/${repoName}/dependency-graph`);
  if (!response.ok) throw new Error(`Dependency graph failed: ${response.status}`);
  return response.json();
}

/**
 * Fetch issue attribution trace
 * @param {string} issueId - Issue ID
 * @returns {Promise<{issue_id: string, attributed: boolean, trace: Object}>}
 */
export async function fetchIssueAttributionTrace(issueId) {
  const response = await fetch(`${API_BASE_URL}/api/issues/${issueId}/attribution-trace`);
  if (!response.ok) throw new Error(`Attribution trace failed: ${response.status}`);
  return response.json();
}

/**
 * Fetch ambiguity queue
 * @param {Object} filters - Optional filters
 * @param {string} [filters.status] - Filter by status
 * @param {string} [filters.priority] - Filter by priority
 * @param {number} [filters.limit=50] - Max records
 * @returns {Promise<{queue: Array, total: number}>}
 */
export async function fetchAmbiguityQueue(filters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.append('status', filters.status);
  if (filters.priority) params.append('priority', filters.priority);
  if (filters.limit) params.append('limit', String(filters.limit));
  
  const response = await fetch(`${API_BASE_URL}/api/ambiguity-queue?${params}`);
  if (!response.ok) throw new Error(`Ambiguity queue failed: ${response.status}`);
  return response.json();
}

/**
 * Resolve ambiguity record
 * @param {string} ambiguityId - Ambiguity ID
 * @param {Object} resolution - Resolution data
 * @param {string} resolution.canonical_id - Selected developer ID
 * @param {string} resolution.resolved_by - Reviewer name
 * @param {string} [resolution.resolution_notes] - Optional notes
 * @returns {Promise<{status: string, ambiguity_id: string}>}
 */
export async function resolveAmbiguity(ambiguityId, resolution) {
  const response = await fetch(`${API_BASE_URL}/api/ambiguity-queue/${ambiguityId}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(resolution),
  });
  if (!response.ok) throw new Error(`Resolve ambiguity failed: ${response.status}`);
  return response.json();
}

/**
 * Fetch attribution system status
 * @returns {Promise<{available: boolean, status: string, engines: Object}>}
 */
export async function fetchAttributionStatus() {
  const response = await fetch(`${API_BASE_URL}/api/attribution/status`);
  if (!response.ok) throw new Error(`Attribution status failed: ${response.status}`);
  return response.json();
}

/**
 * Fetch attribution summary
 * @returns {Promise<{summary: Object, assessment: string}>}
 */
export async function fetchAttributionSummary() {
  const response = await fetch(`${API_BASE_URL}/api/attribution/summary`);
  if (!response.ok) throw new Error(`Attribution summary failed: ${response.status}`);
  return response.json();
}

/**
 * Check if attribution features are available
 * @returns {Promise<boolean>}
 */
export async function isAttributionAvailable() {
  try {
    const status = await fetchAttributionStatus();
    return status.available === true;
  } catch {
    return false;
  }
}

// Default export
export default {
  fetchIdentityStatus,
  fetchDeveloperOwnership,
  fetchDeveloperAttributionHistory,
  fetchManagerTeamAttribution,
  fetchManagerTeamDependencies,
  fetchRepositoryDependencyGraph,
  fetchIssueAttributionTrace,
  fetchAmbiguityQueue,
  resolveAmbiguity,
  fetchAttributionStatus,
  fetchAttributionSummary,
  isAttributionAvailable,
};
