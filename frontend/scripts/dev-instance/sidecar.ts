import fs from 'node:fs';
import path from 'node:path';
import consola from 'consola';
import { z } from 'zod/v4';
import { errorMessage } from './format';
import { atomicWriteJson } from './port-registry';

const SIDECAR_FILENAME = '.rotki-instance.json';

export const SIDECAR_VERSION = 1;

const logger = consola.withTag('dev-instance:sidecar');

const InstanceMetaSchema = z.object({
  version: z.number(),
  name: z.string(),
  portSlot: z.number(),
  branch: z.string().optional(),
  worktreePath: z.string().optional(),
  acceptedManagedEnv: z.boolean().optional(),
  createdAt: z.string().optional(),
  lastUsedAt: z.string().optional(),
});

type ParsedSidecar = z.infer<typeof InstanceMetaSchema>;

export interface InstanceMeta {
  version: number;
  name: string;
  branch?: string;
  worktreePath?: string;
  portSlot: number;
  acceptedManagedEnv?: boolean;
  createdAt: string;
  lastUsedAt: string;
}

function metaPath(dir: string): string {
  return path.join(dir, SIDECAR_FILENAME);
}

function applyMetaDefaults(parsed: ParsedSidecar): InstanceMeta {
  const now = new Date().toISOString();
  return {
    version: SIDECAR_VERSION,
    name: parsed.name,
    portSlot: parsed.portSlot,
    branch: parsed.branch,
    worktreePath: parsed.worktreePath,
    acceptedManagedEnv: parsed.acceptedManagedEnv,
    createdAt: parsed.createdAt ?? now,
    lastUsedAt: parsed.lastUsedAt ?? parsed.createdAt ?? now,
  };
}

export function readMetadata(dir: string): InstanceMeta | null {
  const file = metaPath(dir);
  if (!fs.existsSync(file))
    return null;
  try {
    const parsed: unknown = JSON.parse(fs.readFileSync(file, 'utf-8'));
    const result = InstanceMetaSchema.safeParse(parsed);
    if (!result.success) {
      logger.warn(`Sidecar at ${file} missing required fields, skipping: ${result.error.message}`);
      return null;
    }
    if (result.data.version !== SIDECAR_VERSION) {
      logger.warn(
        `Sidecar at ${file} has version ${result.data.version}, expected ${SIDECAR_VERSION}; `
        + `skipping (add a migrator before bumping SIDECAR_VERSION).`,
      );
      return null;
    }
    return applyMetaDefaults(result.data);
  }
  catch (error) {
    logger.warn(`Failed to read sidecar ${file}: ${errorMessage(error)}`);
    return null;
  }
}

export function writeMetadata(dir: string, meta: InstanceMeta): void {
  fs.mkdirSync(dir, { recursive: true });
  atomicWriteJson(metaPath(dir), meta);
}

export function touchLastUsed(dir: string): void {
  const meta = readMetadata(dir);
  if (!meta) {
    return;
  }
  meta.lastUsedAt = new Date().toISOString();
  writeMetadata(dir, meta);
}
