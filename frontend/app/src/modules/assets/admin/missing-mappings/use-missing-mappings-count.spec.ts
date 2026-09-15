import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';

const { countMappings, logError } = vi.hoisted(() => ({
  countMappings: vi.fn<() => Promise<number>>(),
  logError: vi.fn(),
}));

vi.mock('@/modules/assets/admin/missing-mappings/use-missing-mappings-db', () => ({
  useMissingMappingsDB: (): object => ({ count: countMappings }),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { error: logError },
}));

let scope: ReturnType<typeof effectScope> | undefined;

/**
 * Imports the composable into a fresh module registry, inside a scope the test stops.
 *
 * @remarks
 * `useMissingMappingsCount` is a `createSharedComposable` singleton, so without the reset one test's
 * count would be the next one's starting value.
 */
async function setup(): Promise<ReturnType<typeof import('@/modules/assets/admin/missing-mappings/use-missing-mappings-count')['useMissingMappingsCount']>> {
  vi.resetModules();
  const { useMissingMappingsCount } = await import('@/modules/assets/admin/missing-mappings/use-missing-mappings-count');
  scope = effectScope();
  const result = scope.run(() => useMissingMappingsCount());
  assert(result);
  return result;
}

describe('modules/assets/admin/missing-mappings/use-missing-mappings-count', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should start at zero and read the table on refresh', async () => {
    countMappings.mockResolvedValue(4);
    const { count, refresh } = await setup();

    expect(get(count)).toBe(0);

    await refresh();

    expect(get(count)).toBe(4);
  });

  it('should keep the last count and log when a read fails', async () => {
    countMappings.mockResolvedValueOnce(2).mockRejectedValueOnce(new Error('closed'));
    const { count, refresh } = await setup();

    await refresh();
    await refresh();

    expect(get(count)).toBe(2);
    expect(logError).toHaveBeenCalledOnce();
  });

  it('should go back to zero when the user logs out', async () => {
    countMappings.mockResolvedValue(5);
    const store = useSessionAuthStore();
    store.logged = true;
    const { count, refresh } = await setup();
    await refresh();

    store.logged = false;
    await nextTick();

    expect(get(count)).toBe(0);
  });
});
