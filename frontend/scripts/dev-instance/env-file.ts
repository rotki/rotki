import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { parse as parseDotenv } from 'dotenv';

export const MANAGED_ENV_KEYS = [
  'INSTANCE_NAME',
  'INSTANCE_PORT_SLOT',
  'VITE_BACKEND_URL',
  'VITE_COLIBRI_URL',
  'DEV_PORT',
] as const;

/**
 * Sentinel comments wrapping the dev:web-managed block. The exact string is
 * load-bearing: writeEnvFile and clearManagedEnvBlock locate the block by
 * matching these lines. Changing the wording later would orphan blocks written
 * by older versions of the script.
 */
const BLOCK_START = '# >>> rotki dev:web managed (do not edit by hand)';
const BLOCK_END = '# <<< rotki dev:web managed';

export function loadEnvFile(file: string): Record<string, string> {
  if (!fs.existsSync(file)) {
    return {};
  }
  return parseDotenv(fs.readFileSync(file));
}

/** Returns the key name of an env-file line, or undefined if it isn't a KEY=VAL line. */
function envLineKey(line: string): string | undefined {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith('#'))
    return undefined;
  const eq = trimmed.indexOf('=');
  return eq === -1 ? undefined : trimmed.slice(0, eq).trim();
}

function buildManagedBlock(managed: readonly string[], updates: Record<string, string>): string[] {
  const lines = [BLOCK_START];
  for (const key of managed) {
    if (key in updates)
      lines.push(`${key}=${updates[key]}`);
  }
  lines.push(BLOCK_END);
  return lines;
}

interface RewriteResult {
  /** Lines to write out, in order. */
  kept: string[];
  /** Whether the input contained a START/END block. */
  hadBlock: boolean;
  /** Whether anything was removed/replaced relative to the input. */
  changed: boolean;
}

/**
 * Walks an env file line-by-line and:
 *  - replaces the existing START/END block with `replacement` (or removes the
 *    block entirely if `replacement` is null)
 *  - strips orphan managed keys living OUTSIDE the block (left over from
 *    pre-marker versions or manual edits)
 *  - preserves every other line verbatim
 */
function rewriteEnvBlock(
  lines: string[],
  managed: Set<string>,
  replacement: string[] | null,
): RewriteResult {
  const kept: string[] = [];
  let hadBlock = false;
  let changed = false;
  let inBlock = false;
  let blockEmitted = false;
  for (const rawLine of lines) {
    // Tolerate CRLF line endings: an .env edited on Windows or copied from a
    // CRLF source ends each line with \r after splitting on '\n'. Strip a
    // trailing \r before matching the sentinel comments so the block is
    // detected and not duplicated on every run.
    const line = rawLine.endsWith('\r') ? rawLine.slice(0, -1) : rawLine;
    if (line === BLOCK_START) {
      inBlock = true;
      hadBlock = true;
      changed = true;
      if (replacement && !blockEmitted) {
        kept.push(...replacement);
        blockEmitted = true;
      }
      continue;
    }
    if (line === BLOCK_END) {
      inBlock = false;
      continue;
    }
    if (inBlock)
      continue;
    const key = envLineKey(line);
    if (key !== undefined && managed.has(key)) {
      changed = true;
      continue;
    }
    kept.push(line);
  }
  return { kept, hadBlock, changed };
}

function writeAtomic(file: string, contents: string): void {
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, contents.endsWith('\n') || contents.length === 0 ? contents : `${contents}\n`, 'utf-8');
  fs.renameSync(tmp, file);
}

export function writeEnvFile(
  file: string,
  updates: Record<string, string>,
  opts: { managed: readonly string[] },
): void {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const existing = fs.existsSync(file) ? fs.readFileSync(file, 'utf-8') : '';
  const managed = new Set(opts.managed);
  const newBlock = buildManagedBlock(opts.managed, updates);
  const { kept, hadBlock } = rewriteEnvBlock(existing.split('\n'), managed, newBlock);

  if (!hadBlock) {
    if (kept.length > 0 && kept.at(-1) !== '')
      kept.push('');
    kept.push(...newBlock);
  }

  writeAtomic(file, kept.join('\n'));
}

/**
 * Reads `INSTANCE_NAME` from the managed env block at `file`. Returns
 * undefined if the file or the key is missing. Used to decide whether a
 * cleanup path should erase the env trail (it should only erase a block that
 * belongs to the instance being removed).
 */
export function readManagedInstanceName(file: string): string | undefined {
  if (!fs.existsSync(file))
    return undefined;
  const parsed = parseDotenv(fs.readFileSync(file));
  const name = parsed.INSTANCE_NAME;
  return name && name.length > 0 ? name : undefined;
}

/**
 * Removes the dev:web-managed block (and any orphan managed keys) from `file`.
 * Leaves every unmanaged line untouched. Useful when an instance is cleaned and
 * we want to remove the env trail it wrote.
 */
export function clearManagedEnvBlock(file: string, opts: { managed: readonly string[] } = { managed: MANAGED_ENV_KEYS }): void {
  if (!fs.existsSync(file))
    return;
  const managed = new Set(opts.managed);
  const { kept, changed } = rewriteEnvBlock(fs.readFileSync(file, 'utf-8').split('\n'), managed, null);
  if (!changed)
    return;
  while (kept.length > 0 && kept.at(-1) === '')
    kept.pop();
  writeAtomic(file, kept.join('\n'));
}
