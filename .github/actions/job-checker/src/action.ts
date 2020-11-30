import * as core from '@actions/core'
import * as github from '@actions/github'

export async function getPullRequestFiles(): Promise<string[] | null> {
  const token = core.getInput('token', {required: true})
  const client = github.getOctokit(token)
  const {context} = github
  if (!context.payload.pull_request) {
    return null
  }
  const {number} = context.payload.pull_request

  const {data} = await client.pulls.listFiles({
    ...context.repo,
    pull_number: number
  })

  return data.map(value => value.filename)
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
