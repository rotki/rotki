import type { ComputedRef } from 'vue';
import type { LocationQuery } from 'vue-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAddQuery } from '@/modules/core/common/use-add-query';

/**
 * A local `vue-router` double, narrower than the global one, so the route the composable reads can
 * be set to a bare query without standing up a whole `RouteLocationNormalizedLoaded`.
 */
const router = vi.hoisted(() => {
  const state: { query: LocationQuery } = { query: {} };
  return {
    replace: vi.fn(({ query }: { query: LocationQuery }) => {
      state.query = query;
    }),
    state,
  };
});

vi.mock('vue-router', () => ({
  useRoute: (): ComputedRef<{ query: LocationQuery }> => computed(() => ({ query: router.state.query })),
  useRouter: (): { replace: typeof router.replace } => ({ replace: router.replace }),
}));

describe('useAddQuery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    router.state.query = {};
  });

  it('should do nothing when the route carries no add query', async () => {
    const onAdd = vi.fn();

    const consumed = await useAddQuery(onAdd).consumeAddQuery();

    expect(consumed).toBe(false);
    expect(onAdd).not.toHaveBeenCalled();
    expect(router.replace).not.toHaveBeenCalled();
  });

  it('should open the dialog and clear the query', async () => {
    const onAdd = vi.fn();
    router.state.query = { add: 'true' };

    const consumed = await useAddQuery(onAdd).consumeAddQuery();

    expect(consumed).toBe(true);
    expect(onAdd).toHaveBeenCalledWith({ add: 'true' });
    expect(router.replace).toHaveBeenCalledWith({ query: {} });
    expect(router.state.query).toEqual({});
  });

  it('should hand the handler the query the link carried, not the cleared one', async () => {
    const seen: LocationQuery[] = [];
    router.state.query = { add: 'true', addressToAdd: '0x1' };

    await useAddQuery((query) => {
      seen.push({ ...query });
    }).consumeAddQuery();

    expect(seen).toEqual([{ add: 'true', addressToAdd: '0x1' }]);
  });

  it('should await an async handler before resolving', async () => {
    let opened = false;
    router.state.query = { add: 'true' };

    await useAddQuery(async () => {
      await nextTick();
      opened = true;
    }).consumeAddQuery();

    expect(opened).toBe(true);
  });
});
