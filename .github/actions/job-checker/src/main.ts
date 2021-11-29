import * as core from '@actions/core'
import {
  changeDetected,
  checkForChanges,
  getInputAsArray,
  shouldRun,
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

    const needsToRun = {
      frontend: false,
      backend: false,
      docs: false
    }

    if (await shouldRun()) {
      needsToRun.frontend = true
      needsToRun.backend = true
      needsToRun.docs = true
      // eslint-disable-next-line no-console
      console.info(`[run all] detected, running all tasks`)
    } else if (await shouldSkip()) {
      // eslint-disable-next-line no-console
      console.info(`[skip ci] or [ci skip] detected, skipping all tasks`)
    } else {
      await checkForChanges(files => {
        if (files === null) {
          needsToRun.frontend = true
          needsToRun.backend = true
          needsToRun.docs = true
        } else {
          // eslint-disable-next-line no-console
          console.info(`Checking ${files.length} files of the PR for changes`)
          if (changeDetected(frontendPaths, files)) {
            needsToRun.frontend = true
          }
          if (changeDetected(backendPaths, files)) {
            needsToRun.backend = true
          }
          if (changeDetected(documentationPaths, files)) {
            needsToRun.docs = true
          }
        }
      })
    }

    if (needsToRun.frontend) {
      // eslint-disable-next-line no-console
      console.info(`will run frontend job`)
      core.setOutput(FRONTEND_TASKS, true)
    }

    if (needsToRun.backend) {
      // eslint-disable-next-line no-console
      console.info(`will run backend job`)
      core.setOutput(BACKEND_TASKS, true)
    }

    if (needsToRun.docs) {
      // eslint-disable-next-line no-console
      console.info(`will run docs job`)
      core.setOutput(DOCUMENTATION_TASKS, true)
    }
  } catch (error) {
    if (error instanceof Error) {
      core.setFailed(error.message)
    } else {
      core.setFailed('unknown error')
    }
  }
}

run()
