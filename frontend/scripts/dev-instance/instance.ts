import fs from 'node:fs';
import process from 'node:process';
import consola from 'consola';
import { loadEnvFile, MANAGED_ENV_KEYS, writeEnvFile } from './env-file';
import { formatHostPort, formatPort, humanBytes } from './format';
import { estimateSeedSize, freeDiskBytes, seedInstance } from './fs-walk';
import { getCurrentGitBranch, getCurrentGitWorktree } from './git';
import { resolveInstanceDir, resolveSeedSource, sanitizeName } from './paths';
import { probePortsLive } from './port-probe';
import { allocatePortSlot, type PortSet, portsForSlot } from './port-registry';
import { type InstanceMeta, readMetadata, SIDECAR_VERSION, writeMetadata } from './sidecar';

const logger = consola.withTag('dev-instance:instance');

const SEED_BUFFER_RATIO = 1.1;

export interface InstanceRuntime {
  name: string;
  slot: number;
  dir: string;
  ports: PortSet;
  meta: InstanceMeta;
}

export interface PrepareInstanceOptions {
  name: string;
  slotHint?: number;
  seed: boolean;
  acceptManagedEnv: boolean;
  envFile: string;
  /** Whether VITE_BACKEND_URL should point at the proxy port or directly at the backend port. */
  useProxy: boolean;
  /** When true, include `*.backup` files in the seed copy. Default false. */
  includeBackups?: boolean;
}

function envKeysDiverge(
  envBefore: Record<string, string>,
  desired: Record<string, string>,
): string[] {
  const diverging: string[] = [];
  for (const key of MANAGED_ENV_KEYS) {
    const before = envBefore[key];
    if (before !== undefined && before !== desired[key]) {
      diverging.push(key);
    }
  }
  return diverging;
}

function computeDesiredManagedEnv(name: string, slot: number, ports: PortSet, useProxy: boolean): Record<string, string> {
  return {
    INSTANCE_NAME: name,
    INSTANCE_PORT_SLOT: String(slot),
    VITE_BACKEND_URL: `http://127.0.0.1:${useProxy ? ports.proxy : ports.restApi}`,
    VITE_COLIBRI_URL: `http://127.0.0.1:${ports.colibri}`,
    DEV_PORT: String(ports.dev),
  };
}

async function refuseIfSlotLive(name: string, slot: number): Promise<void> {
  const live = await probePortsLive(slot);
  if (live.length === 0)
    return;
  const lines = [
    `Instance "${name}" is already live on slot ${slot}:`,
    ...live.map((entry) => {
      const pid = entry.pid !== undefined ? ` (PID ${entry.pid})` : '';
      return `  ${entry.name.padEnd(8)} ${formatHostPort('localhost', entry.port)}${pid}`;
    }),
    'Pass --instance <other-name> for a fresh slot or stop the running one.',
  ];
  logger.error(lines.join('\n'));
  process.exit(1);
}

function refuseOnEnvDivergence(
  context: { name: string; slot: number; ports: PortSet },
  envFile: string,
  divergingKeys: string[],
  envBefore: Record<string, string>,
  desiredEnv: Record<string, string>,
): void {
  const { name, slot, ports } = context;
  const portLine = `backend=${formatPort(ports.restApi)} proxy=${formatPort(ports.proxy)} colibri=${formatPort(ports.colibri)} dev=${formatPort(ports.dev)}`;
  const lines = [
    `Instance "${name}" → slot ${slot} (${portLine})`,
    `Detected user-customized managed env keys in ${envFile}:`,
    ...divergingKeys.map(key => `  ${key} = ${envBefore[key]}  (slot ${slot} expects ${desiredEnv[key]})`),
    '',
    'To resolve, pick ONE:',
    '  --accept-managed-env       let dev:web own these keys for this instance',
    '  --no-instance              run today\'s default behaviour, ignore INSTANCE_NAME',
    '  INSTANCE_PORT_SLOT=<slot>  pin the slot whose ports already match your env (slot 0 = defaults)',
    '',
    'Unmanaged keys are always preserved.',
  ];
  logger.error(lines.join('\n'));
  process.exit(1);
}

function seedFromSource(name: string, dir: string, source: string, includeBackups: boolean): void {
  const estimated = estimateSeedSize(source, { includeBackups });
  const free = freeDiskBytes(dir);
  if (free !== undefined && free < estimated * SEED_BUFFER_RATIO) {
    logger.error(
      `Insufficient disk space to seed instance "${name}": `
      + `${humanBytes(free)} free, need ~${humanBytes(estimated)} (+10% buffer).`,
    );
    process.exit(1);
  }
  const backupNote = includeBackups ? ' (including *.backup)' : '';
  logger.info(`Seeding instance "${name}" from ${source}${backupNote} (~${humanBytes(estimated)})…`);
  seedInstance(dir, source, {
    includeBackups,
    onProgress: ({ files, bytes }) => {
      logger.info(`  copied ${files} files, ${humanBytes(bytes)}`);
    },
  });
  logger.success(`Seed complete for "${name}"`);
}

function ensureInstanceData(name: string, dir: string, wantSeed: boolean, includeBackups: boolean): void {
  const needsSeed = !fs.existsSync(dir) || fs.readdirSync(dir).length === 0;
  if (!needsSeed)
    return;
  if (!wantSeed) {
    fs.mkdirSync(dir, { recursive: true });
    return;
  }
  const source = resolveSeedSource();
  if (!source) {
    logger.warn(
      'No rotki seed data dir found (set ROTKI_SEED_SOURCE to override). '
      + 'Creating an empty instance data dir — backend will start with no preloaded assets/users.',
    );
    fs.mkdirSync(dir, { recursive: true });
    return;
  }
  seedFromSource(name, dir, source, includeBackups);
}

function buildMeta(
  name: string,
  slot: number,
  existingMeta: InstanceMeta | null,
  consentNow: boolean,
): InstanceMeta {
  const now = new Date().toISOString();
  if (existingMeta) {
    return {
      ...existingMeta,
      portSlot: slot,
      branch: getCurrentGitBranch() ?? existingMeta.branch,
      worktreePath: getCurrentGitWorktree() ?? existingMeta.worktreePath,
      acceptedManagedEnv: consentNow || existingMeta.acceptedManagedEnv === true,
      lastUsedAt: now,
    };
  }
  return {
    version: SIDECAR_VERSION,
    name,
    portSlot: slot,
    branch: getCurrentGitBranch(),
    worktreePath: getCurrentGitWorktree(),
    acceptedManagedEnv: consentNow,
    createdAt: now,
    lastUsedAt: now,
  };
}

export async function prepareInstance(opts: PrepareInstanceOptions): Promise<InstanceRuntime> {
  const name = sanitizeName(opts.name);
  const dir = resolveInstanceDir(name);
  const slot = await allocatePortSlot(name, opts.slotHint);
  const ports = portsForSlot(slot);

  await refuseIfSlotLive(name, slot);

  const desiredEnv = computeDesiredManagedEnv(name, slot, ports, opts.useProxy);
  const envBefore = loadEnvFile(opts.envFile);
  const existingMeta = readMetadata(dir);
  const alreadyConsented = existingMeta?.acceptedManagedEnv === true;
  const divergingKeys = envKeysDiverge(envBefore, desiredEnv);
  if (divergingKeys.length > 0 && !alreadyConsented && !opts.acceptManagedEnv) {
    refuseOnEnvDivergence({ name, slot, ports }, opts.envFile, divergingKeys, envBefore, desiredEnv);
  }

  ensureInstanceData(name, dir, opts.seed, opts.includeBackups === true);
  writeEnvFile(opts.envFile, desiredEnv, { managed: MANAGED_ENV_KEYS });

  const meta = buildMeta(name, slot, existingMeta, alreadyConsented || opts.acceptManagedEnv || divergingKeys.length === 0);
  writeMetadata(dir, meta);

  return { name, slot, dir, ports, meta };
}
