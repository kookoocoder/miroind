import service from './index'

/**
 * Create a MiroInd exploration run.
 * @param {Object} payload - Brand, text asset, audience, and simulation config.
 */
export const createMiroIndRun = (payload) => {
  return service.post('/api/miroind/runs', payload)
}

/**
 * Read a previously persisted MiroInd exploration run.
 * @param {string} runId
 */
export const getMiroIndRun = (runId) => {
  return service.get(`/api/miroind/runs/${encodeURIComponent(runId)}`)
}
