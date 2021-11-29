import * as core from '@actions/core'
import * as github from '@actions/github'

export async function checkForChanges(
  check: (files: string[] | null) => void
): Promise<void> {
  const token = core.getInput('token', {required: true})
  const client = github.getOctokit(token)
  const {context} = github
  if (!context.payload.pull_request) {
    // eslint-disable-next-line no-console
    console.info(`This is not a PR`)
    check(null)
    return
  }
  const {number} = context.payload.pull_request

  for await (const response of client.paginate.iterator(
    client.rest.pulls.listFiles,
    {
      ...context.repo,
      pull_number: number
    }
  )) {
    check(response.data.map(value => value.filename))
  }
}

async function tagInCommitMessage(tag: RegExp): Promise<boolean> {
  const token = core.getInput('token', {required: true})
  const client = github.getOctokit(token)
  const {context} = github
  if (!context.payload.pull_request) {
    // eslint-disable-next-line no-console
    console.info(`Didn't detect a PR`)
    return false
  }
  const {sha} = context.payload.pull_request.head

  const response = await client.rest.git.getCommit({
    ...context.repo,
    commit_sha: sha
  })

  const {message} = response.data
  return !!message && tag.exec(message) !== null
}

export async function shouldRun(): Promise<boolean> {
  return tagInCommitMessage(/\[run all]/gm)
}

export async function shouldSkip(): Promise<boolean> {
  return tagInCommitMessage(/\[skip ci]|\[ci skip]/gm)
}

export function changeDetected(
  monitored: string[],
  changed: string[]
): boolean {
  for (const path of monitored) {
    for (const detected of changed) {
      if (detected.startsWith(path) || detected === path) {
        return true
      }
    }
  }
  return false
}

export function getInputAsArray(
  name: string,
  options?: core.InputOptions
): string[] {
  return core
    .getInput(name, options)
    .split('\n')
    .map(s => s.trim())
    .filter(x => x !== '')
}
