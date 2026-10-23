import { describe, expect, it } from 'vitest';
import { type ActivityId, ActivityPart, activityParts } from '@/modules/task-center/core/types';

/**
 * Every activity descriptor, found rather than registered, the same way `flows.spec.ts` finds flows.
 *
 * Descriptors live beside their producers as `*.activity.ts`, so nothing enumerates them at
 * runtime; the glob does, at test time only, without a registry that would import every producer.
 */
const modules = import.meta.glob<Record<string, unknown>>('@/modules/**/*.activity.ts', { eager: true });

/** The runtime surface of a descriptor, which is all this spec calls. */
interface Descriptor {
  readonly kind: string;
  readonly id: (subject: unknown) => ActivityId;
  readonly partsOf: (subject: unknown) => readonly (string | number)[];
  readonly batchId: (prefix: readonly []) => ActivityId;
}

interface Declared {
  readonly file: string;
  readonly name: string;
  readonly descriptor: Descriptor;
}

function isDescriptor(value: unknown): value is Descriptor {
  if (typeof value !== 'object' || value === null)
    return false;

  return 'kind' in value && typeof value.kind === 'string'
    && 'id' in value && typeof value.id === 'function'
    && 'partsOf' in value && typeof value.partsOf === 'function'
    && 'batchId' in value && typeof value.batchId === 'function';
}

const declared: Declared[] = Object.entries(modules).flatMap(([file, exported]) =>
  Object.entries(exported)
    .filter((entry): entry is [string, Descriptor] => isDescriptor(entry[1]))
    .map(([name, descriptor]) => ({ descriptor, file, name })),
);

const address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

/**
 * Realistic subjects per descriptor, by export name.
 *
 * Keyed by name rather than imported, so this spec does not grow an import per activity file.
 * The price is that a sample is not type-checked against its descriptor; a sample of the wrong
 * shape shows up as an empty or `undefined` part, which a test below rejects.
 */
const samples = new Map<string, readonly unknown[]>([
  ['accountAddActivity', [
    { chain: 'eth', target: { address, kind: 'address' } },
    { chain: 'EVM', target: { addresses: [address, '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045'], kind: 'addresses' } },
    { chain: 'btc', target: { derivationPath: 'm/0\'/0', kind: 'xpub', xpub: 'xpub6CUGRUonZSQ4TWtTMmzXdrXDtypWKiKrhko4egpiMZbpiaQL2jkwSB1icqYh2cfDfVxdx4df189oLKnC5fSwqPfgyP3hooxujYzAu3fDVmz' } },
  ]],
  ['accountAgnosticRemoveActivity', [{ address, category: 'evm' }]],
  ['accountImportActivity', [{ source: 'csv' }]],
  ['accountRemoveActivity', [
    { chain: 'eth', target: { address, kind: 'address' } },
    { chain: 'btc', target: { kind: 'xpub', xpub: 'xpub6CUGRUonZSQ4TWtTMmzXdrXDtypWKiKrhko4egpiMZbpiaQL2jkwSB1icqYh2cfDfVxdx4df189oLKnC5fSwqPfgyP3hooxujYzAu3fDVmz' } },
  ]],
  ['accountSyncActivity', [{ address, chain: 'eth' }]],
  ['bankEventsActivity', [{ location: 'bank', name: 'Checking' }]],
  ['blockDecodeActivity', [{ blockNumbers: [19000002, 19000001] }]],
  ['chainSyncActivity', [{ chain: 'eth' }]],
  ['decodeActivity', [{ chain: 'eth', ignoreCache: false }, { chain: 'eth', ignoreCache: true }]],
  ['exchangeEventsActivity', [{ location: 'kraken', name: 'Main' }]],
  ['onlineEventsActivity', [{ queryType: 'eth_withdrawals' }]],
  ['protocolCacheActivity', [undefined]],
  ['targetedDecodeActivity', [{ chain: 'eth', txRefs: ['0x02', '0x01'] }]],
]);

const sampled = declared.flatMap(({ descriptor, name }) =>
  (samples.get(name) ?? []).map(subject => ({ descriptor, name, subject })),
);

const sampledIds: ActivityId[] = sampled.map(({ descriptor, subject }) => descriptor.id(subject));

describe('activity descriptors', () => {
  it('should find at least one declared descriptor, without which every test below passes vacuously', () => {
    expect(declared.length).toBeGreaterThan(0);
  });

  it('should not export two descriptors under one name, since samples are keyed by it', () => {
    const names = declared.map(({ name }) => name);
    expect(new Set(names).size).toBe(names.length);
  });

  it.each(declared.map(d => [d.name, d] as const))('%s should have a sample subject in this spec', (name) => {
    expect(samples.get(name)?.length, `add a sample subject for ${name}`).toBeGreaterThan(0);
  });

  it('should hold no sample for a descriptor that no longer exists', () => {
    const names = new Set(declared.map(({ name }) => name));
    expect([...samples.keys()].filter(name => !names.has(name))).toStrictEqual([]);
  });

  it.each(sampled.map(s => [s.name, s] as const))('%s should recover its parts from its id, which is what every coarse reader relies on', (_name, { descriptor, subject }) => {
    const id = descriptor.id(subject);

    expect(id.startsWith(`${descriptor.kind}:`) || id === descriptor.kind).toBe(true);
    expect(activityParts(id)).toStrictEqual(descriptor.partsOf(subject).map(String));
  });

  it.each(sampled.map(s => [s.name, s] as const))('%s should build no empty or undefined part, the mark of a sample or key of the wrong shape', (_name, { descriptor, subject }) => {
    for (const part of descriptor.partsOf(subject).map(String)) {
      expect(part).not.toBe('');
      expect(part).not.toBe('undefined');
    }
  });

  it('should give every sampled subject its own id, so no two requests dedup onto one promise', () => {
    expect(new Set(sampledIds).size).toBe(sampledIds.length);
  });

  it.each(declared.map(d => [d.name, d] as const))('%s should keep its batch umbrella apart from every subject id', (_name, { descriptor }) => {
    const batchId = descriptor.batchId([]);

    expect(activityParts(batchId).at(-1)).toBe(ActivityPart.BATCH);
    expect(sampledIds).not.toContain(batchId);
  });
});
