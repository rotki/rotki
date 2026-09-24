import type { ComputedRef } from 'vue';
import type { LocationQuery } from 'vue-router';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAddQuery } from '@/modules/core/common/use-add-query';

/**
 * A local `vue-router` double, narrower than the global one, so the route the composable reads can
 * be set to a bare query without standing up a whole `RouteLocationNormalizedLoaded`.
 */
const query = ref<LocationQuery>({});

const router = vi.hoisted(() => ({ replace: vi.fn() }));

vi.mock('vue-router', () => ({
  useRoute: (): ComputedRef<{ query: LocationQuery }> => computed(() => ({ query: get(query) })),
  useRouter: (): { replace: typeof router.replace } => ({ replace: router.replace }),
}));

let scope: ReturnType<typeof effectScope> | undefined;

function addQuery(onAdd: Parameters<typeof useAddQuery>[0]): ReturnType<typeof useAddQuery> {
  scope = effectScope();
  return scope.run(() => useAddQuery(onAdd))!;
}

describe('useAddQuery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(query, {});
    router.replace.mockImplementation(({ query: next }: { query: LocationQuery }) => {
      set(query, next);
    });
  });

  afterEach(() => {
    scope?.stop();
    scope = undefined;
  });

  it('should do nothing when the route carries no add query', async () => {
    const onAdd = vi.fn();

    const consumed = await addQuery(onAdd).consumeAddQuery();

    expect(consumed).toBe(false);
    expect(onAdd).not.toHaveBeenCalled();
    expect(router.replace).not.toHaveBeenCalled();
  });

  it('should open the dialog and clear the query', async () => {
    const onAdd = vi.fn();
    set(query, { add: 'true' });

    const consumed = await addQuery(onAdd).consumeAddQuery();

    expect(consumed).toBe(true);
    expect(onAdd).toHaveBeenCalledWith({ add: 'true' });
    expect(router.replace).toHaveBeenCalledWith({ query: {} });
    expect(get(query)).toEqual({});
  });

  it('should hand the handler the query the link carried, not the cleared one', async () => {
    const seen: LocationQuery[] = [];
    set(query, { add: 'true', addressToAdd: '0x1' });

    await addQuery((carried) => {
      seen.push({ ...carried });
    }).consumeAddQuery();

    expect(seen).toEqual([{ add: 'true', addressToAdd: '0x1' }]);
  });

  it('should await an async handler before resolving', async () => {
    let opened = false;
    set(query, { add: 'true' });

    await addQuery(async () => {
      await nextTick();
      opened = true;
    }).consumeAddQuery();

    expect(opened).toBe(true);
  });

  it('should open the dialog for a link that arrives while the page is already open, once', async () => {
    const onAdd = vi.fn();
    addQuery(onAdd);

    set(query, { add: 'true', addressToAdd: '0x1' });
    await flushPromises();

    expect(onAdd).toHaveBeenCalledExactlyOnceWith({ add: 'true', addressToAdd: '0x1' });
    expect(get(query)).toEqual({});
  });
});
