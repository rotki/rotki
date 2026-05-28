import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { confirm, isCancel } from '@clack/prompts';
import consola from 'consola';
import { clearManagedEnvBlock, readManagedInstanceName } from './env-file';
import { formatHostPort, formatTable, humanBytes } from './format';
import { dirSizeBytes } from './fs-walk';
import { liveWorktreePaths } from './git';
import { resolveInstanceDir, resolveInstanceParent, sanitizeName } from './paths';
import { probePortsLive } from './port-probe';
import { readPortIndex, releasePortSlot, writePortIndex } from './port-registry';
import { type InstanceMeta, readMetadata } from './sidecar';

const logger = consola.withTag('dev-instance:lifecycle');

export interface InstanceSummary {
  name: string;
  dir: string;
  meta: InstanceMeta | null;
  sizeBytes: number;
  worktreeExists: boolean;
  live: boolean;
}

export async function listInstances(): Promise<InstanceSummary[]> {
  const parent = resolveInstanceParent();
  if (!fs.existsSync(parent)) {
    return [];
  }
  const worktrees = liveWorktreePaths();
  const dirEntries = fs.readdirSync(parent, { withFileTypes: true }).filter(e => e.isDirectory());
  const summaries = await Promise.all(dirEntries.map(async (entry) => {
    const dir = path.join(parent, entry.name);
    const meta = readMetadata(dir);
    const live = meta ? (await probePortsLive(meta.portSlot)).length > 0 : false;
    return {
      name: meta?.name ?? entry.name,
      dir,
      meta,
      sizeBytes: dirSizeBytes(dir),
      worktreeExists: meta?.worktreePath ? worktrees.has(meta.worktreePath) : false,
      live,
    } satisfies InstanceSummary;
  }));
  summaries.sort((a, b) => {
    const aTs = a.meta?.lastUsedAt ?? '';
    const bTs = b.meta?.lastUsedAt ?? '';
    return bTs.localeCompare(aTs);
  });
  return summaries;
}

function formatWorktreeStatus(s: InstanceSummary): string {
  if (!s.meta?.worktreePath)
    return '-';
  return s.worktreeExists ? 'yes' : 'missing';
}

export async function printInstanceList(): Promise<void> {
  const summaries = await listInstances();
  if (summaries.length === 0) {
    logger.info(`No instances under ${resolveInstanceParent()}`);
    return;
  }
  const header = ['NAME', 'BRANCH', 'WORKTREE', 'SLOT', 'SIZE', 'LAST USED', 'LIVE'];
  const rows: string[][] = [header];
  for (const s of summaries) {
    rows.push([
      s.name,
      s.meta?.branch ?? '-',
      formatWorktreeStatus(s),
      s.meta?.portSlot !== undefined ? String(s.meta.portSlot) : '?',
      humanBytes(s.sizeBytes),
      s.meta?.lastUsedAt ? s.meta.lastUsedAt.replace('T', ' ').slice(0, 19) : '-',
      s.live ? 'yes' : 'no',
    ]);
  }
  console.log(formatTable(rows));
}

/**
 * If `envFile` is provided and its managed block names `instanceName`, strip
 * the block. This keeps stale `VITE_BACKEND_URL` / `INSTANCE_NAME` etc. from
 * pointing at a slot whose data dir we just deleted. We never touch a block
 * that belongs to a *different* still-live instance.
 */
function clearEnvBlockIfOwned(envFile: string | undefined, instanceName: string): void {
  if (!envFile)
    return;
  const owner = readManagedInstanceName(envFile);
  if (owner === undefined)
    return;
  if (sanitizeName(owner) !== sanitizeName(instanceName))
    return;
  clearManagedEnvBlock(envFile);
  logger.info(`Cleared managed env block for "${instanceName}" from ${envFile}`);
}

export async function refuseIfLive(name: string, slot: number): Promise<boolean> {
  const live = await probePortsLive(slot);
  if (live.length === 0) {
    return false;
  }
  const lines = [
    `Instance "${name}" is live on slot ${slot}:`,
    ...live.map((entry) => {
      const pid = entry.pid !== undefined ? ` (PID ${entry.pid})` : '';
      return `  ${entry.name.padEnd(8)} ${formatHostPort('localhost', entry.port)}${pid}`;
    }),
    'Stop the running instance before continuing.',
  ];
  logger.error(lines.join('\n'));
  return true;
}

export async function cleanInstance(name: string, opts: { yes?: boolean; envFile?: string } = {}): Promise<void> {
  const sanitized = sanitizeName(name);
  const dir = resolveInstanceDir(sanitized);
  if (!fs.existsSync(dir)) {
    logger.warn(`Instance "${sanitized}" does not exist at ${dir}`);
    await releasePortSlot(sanitized);
    clearEnvBlockIfOwned(opts.envFile, sanitized);
    return;
  }
  const meta = readMetadata(dir);
  const slot = meta?.portSlot ?? readPortIndex().slots[sanitized];
  if (slot !== undefined && await refuseIfLive(sanitized, slot)) {
    process.exitCode = 1;
    return;
  }
  if (!opts.yes) {
    const answer = await confirm({ message: `Delete instance "${sanitized}" at ${dir}?`, initialValue: false });
    if (isCancel(answer) || !answer) {
      logger.info('Aborted.');
      return;
    }
  }
  fs.rmSync(dir, { recursive: true, force: true });
  await releasePortSlot(sanitized);
  clearEnvBlockIfOwned(opts.envFile, sanitized);
  logger.success(`Removed instance "${sanitized}"`);
}

async function removeSummary(s: InstanceSummary, envFile?: string): Promise<void> {
  if (s.meta?.portSlot !== undefined && await refuseIfLive(s.name, s.meta.portSlot)) {
    logger.error(`Skipping "${s.name}" because it is live.`);
    process.exitCode = 1;
    return;
  }
  fs.rmSync(s.dir, { recursive: true, force: true });
  await releasePortSlot(s.name);
  clearEnvBlockIfOwned(envFile, s.name);
  logger.success(`Removed "${s.name}"`);
}

async function confirmedYes(message: string): Promise<boolean> {
  const answer = await confirm({ message, initialValue: false });
  return !isCancel(answer) && answer === true;
}

function describeCleanAllPlan(parent: string, summaries: InstanceSummary[]): void {
  const instanceCount = summaries.filter(s => s.meta).length;
  const orphanCount = summaries.length - instanceCount;
  const headline = orphanCount > 0
    ? `About to remove ${instanceCount} instance(s) + ${orphanCount} orphan dir(s) under: ${parent}`
    : `About to remove ${instanceCount} instance(s) under: ${parent}`;
  logger.warn(headline);
  for (const s of summaries) {
    const label = s.meta ? 'instance' : 'orphan — no sidecar';
    logger.warn(`  - ${s.name} (${label}) at ${s.dir}`);
  }
}

export async function cleanAll(opts: { yes?: boolean; envFile?: string } = {}): Promise<void> {
  const parent = resolveInstanceParent();
  const summaries = await listInstances();
  if (summaries.length === 0) {
    logger.info(`No instances to clean under ${parent}`);
    return;
  }
  describeCleanAllPlan(parent, summaries);
  if (!opts.yes) {
    if (!await confirmedYes(`Remove ALL ${summaries.length} entries?`)) {
      logger.info('Aborted.');
      return;
    }
    if (!await confirmedYes(`Really delete every directory under ${parent}?`)) {
      logger.info('Aborted.');
      return;
    }
  }
  for (const s of summaries) {
    await removeSummary(s, opts.envFile);
  }
}

function parseDuration(raw: string): number {
  const match = raw.match(/^(\d+)([dhm])$/);
  if (!match) {
    throw new Error(`Invalid duration "${raw}", expected formats like 30d, 12h, 45m`);
  }
  const value = Number.parseInt(match[1], 10);
  const unit = match[2];
  const unitMs: Record<string, number> = { d: 86_400_000, h: 3_600_000, m: 60_000 };
  return value * unitMs[unit];
}

function isPruneCandidate(s: InstanceSummary, olderThanMs: number | undefined, now: number): boolean {
  if (!s.meta)
    return false;
  const worktreeGone = !!s.meta.worktreePath && !s.worktreeExists;
  if (!worktreeGone)
    return false;
  if (olderThanMs === undefined)
    return true;
  const lastUsed = Date.parse(s.meta.lastUsedAt);
  return !Number.isFinite(lastUsed) || now - lastUsed >= olderThanMs;
}

async function executePrune(targets: InstanceSummary[], envFile?: string): Promise<void> {
  for (const t of targets) {
    if (t.meta && await refuseIfLive(t.name, t.meta.portSlot)) {
      logger.error(`Skipping "${t.name}" because it is live.`);
      process.exitCode = 1;
      continue;
    }
    fs.rmSync(t.dir, { recursive: true, force: true });
    await releasePortSlot(t.name);
    clearEnvBlockIfOwned(envFile, t.name);
    logger.success(`Pruned "${t.name}"`);
  }
}

export async function pruneInstances(opts: { yes?: boolean; olderThan?: string; envFile?: string } = {}): Promise<void> {
  const olderThanMs = opts.olderThan ? parseDuration(opts.olderThan) : undefined;
  const now = Date.now();
  const summaries = await listInstances();
  const targets = summaries.filter(s => isPruneCandidate(s, olderThanMs, now));
  if (targets.length === 0) {
    logger.info('No prune candidates found.');
    return;
  }
  logger.info(`${opts.yes ? 'Pruning' : 'Would prune'} ${targets.length} instance(s):`);
  for (const t of targets) {
    logger.info(`  - ${t.name} (worktree ${t.meta?.worktreePath ?? '?'}, lastUsed ${t.meta?.lastUsedAt})`);
  }
  if (!opts.yes) {
    logger.info('Re-run with --yes to delete.');
    return;
  }
  await executePrune(targets, opts.envFile);
}

export async function repairRegistry(opts: { yes?: boolean } = {}): Promise<void> {
  const summaries = await listInstances();
  const rebuilt: Record<string, number> = {};
  for (const s of summaries) {
    if (s.meta) {
      rebuilt[sanitizeName(s.meta.name)] = s.meta.portSlot;
    }
  }
  const current = readPortIndex();
  const stableStringify = (obj: Record<string, number>): string => {
    const sorted: Record<string, number> = {};
    for (const k of Object.keys(obj).sort()) sorted[k] = obj[k];
    return JSON.stringify(sorted, null, 2);
  };
  const before = stableStringify(current.slots);
  const after = stableStringify(rebuilt);
  if (before === after) {
    logger.info('Port index already matches sidecars. Nothing to do.');
    return;
  }
  logger.info('Port-index diff:');
  logger.info(`  before: ${before}`);
  logger.info(`  after:  ${after}`);
  if (!opts.yes) {
    logger.info('Re-run with --yes to write.');
    return;
  }
  writePortIndex({ version: 1, slots: rebuilt });
  logger.success('Port index rebuilt from sidecars.');
}
