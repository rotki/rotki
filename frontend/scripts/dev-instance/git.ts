import { execSync } from 'node:child_process';
import consola from 'consola';

import { errorMessage } from './format';

const logger = consola.withTag('dev-instance:git');

export function getCurrentGitBranch(): string | undefined {
  try {
    const out = execSync('git rev-parse --abbrev-ref HEAD', {
      encoding: 'utf-8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
    return out === 'HEAD' || out.length === 0 ? undefined : out;
  }
  catch {
    return undefined;
  }
}

export function getCurrentGitWorktree(): string | undefined {
  try {
    return execSync('git rev-parse --show-toplevel', {
      encoding: 'utf-8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim() || undefined;
  }
  catch {
    return undefined;
  }
}

export function liveWorktreePaths(): Set<string> {
  try {
    const raw = execSync('git worktree list --porcelain', { encoding: 'utf-8' });
    const paths = new Set<string>();
    for (const line of raw.split('\n')) {
      if (line.startsWith('worktree ')) {
        paths.add(line.slice('worktree '.length).trim());
      }
    }
    return paths;
  }
  catch (error) {
    logger.warn(`Failed to list git worktrees: ${errorMessage(error)}`);
    return new Set();
  }
}
