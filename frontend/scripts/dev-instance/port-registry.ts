import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import consola from 'consola';
import { z } from 'zod/v4';
import { errorCode, errorMessage } from './format';
import { ensureInstanceParent, resolveInstanceParent, sanitizeName } from './paths';

export const DEFAULT_PORTS = {
  restApi: 4242,
  proxy: 4243,
  colibri: 4343,
  dev: 8080,
} as const;

export type PortName = keyof typeof DEFAULT_PORTS;

/** Highest valid TCP port (IANA, 16-bit unsigned). */
export const MAX_PORT = 65_535;

/**
 * Instance slots ≥ 1 are packed into a tight contiguous block starting here.
 * Picked because:
 *   - it is above Chromium's last restricted port (10080 = amanda); the old
 *     layout (defaults + slot*200) put slot 10's dev port on 10080, which
 *     Chrome/Vivaldi refuse to load.
 *   - it is far below the e2e fixed ports (30301–30304 in playwright.config.ts).
 *   - it is well inside the user range (1024–49151), nowhere near ephemeral.
 */
export const INSTANCE_BASE_PORT = 13_000;

/**
 * Each slot owns 4 contiguous ports (backend, proxy, colibri, dev). A step of
 * 10 leaves 6 ports of slack between neighbours so TIME_WAIT sockets from one
 * slot can't bleed into the next. With the 1000-slot cap below, the highest
 * port we'd ever pick is 13_000 + 999*10 + 3 = 22_993.
 */
export const INSTANCE_SLOT_STEP = 10;

/** First slot index handed out by the allocator. Slot 0 = `DEFAULT_PORTS`,
 *  reserved for the non-instance ("plain `pnpm dev`") case. */
export const RESERVED_SLOTS_END = 1;

const NODE_INSPECT_PORT = 9229;
const PORT_INDEX_FILENAME = '.port-index.json';

/**
 * Ports we must never allocate to a dev instance, even if the math lands on
 * them. Currently:
 *   - 9229: default node --inspect port; a slot landing here breaks debugger
 *     attach.
 *   - 30301–30304: hard-coded e2e ports (playwright.config.ts). Running an
 *     instance on one of these would clash with a Playwright run.
 */
const RESERVED_PORTS = new Set<number>([NODE_INSPECT_PORT, 30_301, 30_302, 30_303, 30_304]);

export interface PortSet {
  restApi: number;
  proxy: number;
  colibri: number;
  dev: number;
}

const PortIndexSchema = z.object({
  version: z.number().default(1),
  slots: z.record(z.string(), z.number()).default({}),
});

export type PortIndex = z.infer<typeof PortIndexSchema>;

const logger = consola.withTag('dev-instance:port-registry');

export function portsForSlot(slot: number): PortSet {
  if (slot === 0) {
    return { ...DEFAULT_PORTS };
  }
  // Layout within a slot's block: dev sits on the base port so the URL you
  // open in the browser is the "round" number (e.g. 13000), and the three
  // backend services follow in order python → proxy → colibri.
  const base = INSTANCE_BASE_PORT + (slot - 1) * INSTANCE_SLOT_STEP;
  return {
    dev: base,
    restApi: base + 1,
    proxy: base + 2,
    colibri: base + 3,
  };
}

function slotHasReservedConflict(slot: number): boolean {
  if (slot < 1)
    return true; // slot 0 belongs to the default (non-instance) mode
  const ports = portsForSlot(slot);
  return Object.values(ports).some(p => p > MAX_PORT || RESERVED_PORTS.has(p));
}

export function readPortIndex(): PortIndex {
  const file = path.join(resolveInstanceParent(), PORT_INDEX_FILENAME);
  if (!fs.existsSync(file)) {
    return { version: 1, slots: {} };
  }
  try {
    const parsed: unknown = JSON.parse(fs.readFileSync(file, 'utf-8'));
    const result = PortIndexSchema.safeParse(parsed);
    if (!result.success) {
      logger.warn(`Port index at ${file} has unexpected shape, ignoring: ${result.error.message}`);
      return { version: 1, slots: {} };
    }
    return result.data;
  }
  catch (error) {
    logger.warn(`Failed to read port index at ${file}: ${errorMessage(error)}`);
    return { version: 1, slots: {} };
  }
}

export function atomicWriteJson(file: string, value: unknown): void {
  const tmp = `${file}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(tmp, `${JSON.stringify(value, null, 2)}\n`, 'utf-8');
  fs.renameSync(tmp, file);
}

export function writePortIndex(index: PortIndex): void {
  ensureInstanceParent();
  atomicWriteJson(path.join(resolveInstanceParent(), PORT_INDEX_FILENAME), index);
}

const LOCK_DIR_NAME = '.port-index.lock';
const LOCK_STALE_MS = 10_000;
const LOCK_POLL_MS = 50;
const LOCK_MAX_WAIT_MS = 5_000;

export async function withRegistryLock<T>(fn: () => Promise<T> | T): Promise<T> {
  ensureInstanceParent();
  const lockDir = path.join(resolveInstanceParent(), LOCK_DIR_NAME);
  const start = Date.now();
  while (true) {
    try {
      fs.mkdirSync(lockDir);
      break;
    }
    catch (error) {
      if (errorCode(error) !== 'EEXIST') {
        throw error;
      }
      try {
        const age = Date.now() - fs.statSync(lockDir).mtimeMs;
        if (age > LOCK_STALE_MS) {
          logger.warn(`Removing stale port-index lock (${age}ms old)`);
          fs.rmSync(lockDir, { recursive: true, force: true });
          continue;
        }
      }
      catch {
        continue;
      }
      if (Date.now() - start > LOCK_MAX_WAIT_MS) {
        throw new Error(`Timed out waiting for port-index lock at ${lockDir}`);
      }
      await new Promise(resolve => setTimeout(resolve, LOCK_POLL_MS));
    }
  }
  try {
    return await fn();
  }
  finally {
    try {
      fs.rmSync(lockDir, { recursive: true, force: true });
    }
    catch {
      // best-effort
    }
  }
}

/**
 * Thrown by `allocatePortSlot` for conditions a developer can resolve (slot
 * conflicts, exhausted range). The CLI catches these and prints `.message`
 * without a stack trace.
 */
export class PortSlotAllocationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'PortSlotAllocationError';
  }
}

function isSlotInUse(index: PortIndex, slot: number, exceptName?: string): boolean {
  for (const [name, s] of Object.entries(index.slots)) {
    if (s === slot && name !== exceptName) {
      return true;
    }
  }
  return false;
}

export async function allocatePortSlot(name: string, hint?: number): Promise<number> {
  const sanitized = sanitizeName(name);
  return withRegistryLock(() => {
    const index = readPortIndex();

    if (hint !== undefined) {
      if (slotHasReservedConflict(hint)) {
        throw new PortSlotAllocationError(
          `Port slot ${hint} resolves to a reserved port (node --inspect on ${NODE_INSPECT_PORT}, the e2e ports 30301–30304) or exceeds the max TCP port.\n`
          + `  Pick a different slot (1 or higher) or unset INSTANCE_PORT_SLOT.`,
        );
      }
      if (isSlotInUse(index, hint, sanitized)) {
        const owner = Object.entries(index.slots).find(([n, s]) => s === hint && n !== sanitized)?.[0];
        throw new PortSlotAllocationError(
          `Port slot ${hint} is already owned by instance "${owner}", not "${sanitized}".\n`
          + `  To resolve, pick ONE:\n`
          + `    --clean ${owner}              free the slot by removing that instance\n`
          + `    INSTANCE_PORT_SLOT=<other>    pick a different slot\n`
          + `    unset INSTANCE_PORT_SLOT      let dev:web allocate a fresh slot for "${sanitized}"`,
        );
      }
      index.slots[sanitized] = hint;
      writePortIndex(index);
      return hint;
    }

    const existing = index.slots[sanitized];
    if (existing !== undefined) {
      return existing;
    }

    let slot = RESERVED_SLOTS_END;
    while (isSlotInUse(index, slot) || slotHasReservedConflict(slot)) {
      slot += 1;
      if (slot > 1000) {
        throw new PortSlotAllocationError('Unable to allocate a free port slot (exhausted search space).');
      }
    }
    index.slots[sanitized] = slot;
    writePortIndex(index);
    return slot;
  });
}

export async function releasePortSlot(name: string): Promise<void> {
  const sanitized = sanitizeName(name);
  await withRegistryLock(() => {
    const index = readPortIndex();
    if (!(sanitized in index.slots)) {
      return;
    }
    delete index.slots[sanitized];
    writePortIndex(index);
  });
}
