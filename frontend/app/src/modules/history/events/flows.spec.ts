import type { AnyHistoryFlow } from '@/modules/history/events/flows';
import { describe, expect, it } from 'vitest';
import en from '@/locales/en.json';

/**
 * Every flow declaration, found rather than registered.
 *
 * Declarations are co-located with their producers, so there is no central list to fall out of
 * date — and no dependency hub pulling every producer into whatever imports it. The cost of that
 * choice is that nothing enumerates them at runtime, which is exactly what this recovers: the glob
 * finds each `*.flow.ts` at test time, so a flow cannot be missed by forgetting to register it.
 *
 * Three flows were missed from a hand-built inventory precisely because they lived outside the
 * module being read. This is the guard against repeating that.
 */
const modules = import.meta.glob<Record<string, unknown>>('@/modules/**/*.flow.ts', { eager: true });

interface Declared {
  readonly file: string;
  readonly name: string;
  readonly flow: AnyHistoryFlow;
}

function isFlow(value: unknown): value is AnyHistoryFlow {
  if (typeof value !== 'object' || value === null)
    return false;

  return 'kind' in value && typeof value.kind === 'string'
    && 'id' in value && typeof value.id === 'function';
}

const flows: Declared[] = Object.entries(modules).flatMap(([file, exported]) =>
  Object.entries(exported)
    .filter((entry): entry is [string, AnyHistoryFlow] => isFlow(entry[1]))
    .map(([name, flow]) => ({ file, flow, name })),
);

describe('history flow declarations', () => {
  it('should find at least one declared flow', () => {
    // A glob that silently matches nothing would make every assertion below vacuous.
    expect(flows.length).toBeGreaterThan(0);
  });

  it.each(flows.map(f => [f.name, f] as const))('%s should have a title that exists in the locale', (_name, declared) => {
    // Presence, not type: the i18n plugin compiles locale leaves, so a translated key is a compiled
    // node here rather than a string. A key that does not exist is plainly undefined.
    const value = declared.flow.titleKey
      .split('.')
      .reduce<unknown>((node, key) => (typeof node === 'object' && node !== null && key in node ? Reflect.get(node, key) : undefined), en);

    expect(value, `missing i18n key: ${declared.flow.titleKey}`).toBeDefined();
  });

  it.each(flows.map(f => [f.name, f] as const))('%s should build an id under its own kind', (_name, declared) => {
    // The id is what dedups re-entry, so it has to actually belong to the kind it claims.
    expect(declared.flow.id().startsWith(declared.flow.kind)).toBe(true);
  });

  it('should not have two flows sharing an id', () => {
    const ids = flows.map(declared => declared.flow.id());
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('should declare every flow beside a producer, not in a shared registry', () => {
    // The co-location contract: a declaration lives in the module whose work it names.
    for (const declared of flows)
      expect(declared.file).toMatch(/\/modules\/.+\.flow\.ts$/);
  });
});
