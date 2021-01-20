import * as core from '@actions/core'
import {
  changeDetected,
  getInputAsArray,
  getPullRequestFiles,
  shouldSkip
} from './action'

const BACKEND_PATHS = 'backend_paths'
const FRONTEND_PATHS = 'frontend_paths'
const DOCUMENTATION_PATHS = 'documentation_paths'

const FRONTEND_TASKS = 'frontend_tasks'
const BACKEND_TASKS = 'backend_tasks'
const DOCUMENTATION_TASKS = 'documentation_tasks'

async function run(): Promise<void> {
  try {
    const options = {required: true}
    const backendPaths = getInputAsArray(BACKEND_PATHS, options)
    const frontendPaths = getInputAsArray(FRONTEND_PATHS, options)
    const documentationPaths = getInputAsArray(DOCUMENTATION_PATHS, options)

    const skip = await shouldSkip()
    if (skip) {
      // eslint-disable-next-line no-console
      console.info(`[skip ci] or [ci skip] detected, skipping all tasks`)
      return
    }

    const changes = await getPullRequestFiles()

    if (changes === null) {
      core.setOutput(FRONTEND_TASKS, true)
      core.setOutput(BACKEND_TASKS, true)
      core.setOutput(DOCUMENTATION_TASKS, true)
      return
    }

    if (changeDetected(frontendPaths, changes)) {
      core.setOutput(FRONTEND_TASKS, true)
    }

    if (changeDetected(backendPaths, changes)) {
      core.setOutput(BACKEND_TASKS, true)
    }

    if (changeDetected(documentationPaths, changes)) {
      core.setOutput(DOCUMENTATION_TASKS, true)
    }
  } catch (error) {
    core.setFailed(error.message)
  }
}

run()
