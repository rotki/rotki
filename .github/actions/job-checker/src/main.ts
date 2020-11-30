import * as core from '@actions/core'
import {changeDetected, getInputAsArray, getPullRequestFiles} from './action'

async function run(): Promise<void> {
  try {
    const options = {required: true}
    const backendPaths = getInputAsArray('backend_paths', options)
    const frontendPaths = getInputAsArray('frontend_paths', options)
    const documentationPaths = getInputAsArray('documentation_paths', options)

    const changes = await getPullRequestFiles()

    if (changes === null) {
      core.setOutput('frontend_tasks', true)
      core.setOutput('backend_tasks', true)
      core.setOutput('documentation_tasks', true)
      return
    }

    if (changeDetected(frontendPaths, changes)) {
      core.setOutput('frontend_tasks', true)
    }

    if (changeDetected(backendPaths, changes)) {
      core.setOutput('backend_tasks', true)
    }

    if (changeDetected(documentationPaths, changes)) {
      core.setOutput('documentation_tasks', true)
    }
  } catch (error) {
    core.setFailed(error.message)
  }
}

run()
