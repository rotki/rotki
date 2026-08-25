import type { VueWrapper } from '@vue/test-utils';
import type { Airdrops } from '@/modules/airdrops/airdrops';
import type { AirdropWithIndex } from '@/pages/airdrops/airdrop-rows';
import { bigNumberify } from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type MaybeRefOrGetter, nextTick, type Ref } from 'vue';
import { useAirdropsPage } from './use-airdrops-page';

const ADDRESS_A = '0xaaa';
const ADDRESS_B = '0xbbb';

// Everything the mocks capture on mount. Filled in by the factories below, read back through the
// accessors, which fail loudly rather than yielding undefined when the page was never mounted.
const { airdropsRef, eligibleAddresses, fetchAirdrops, rememberSorting, selectedAddresses, status } = vi.hoisted(() => {
  const airdropsRef: { current?: Ref<Airdrops> } = {};
  /** What the page hands `useAirdropFields` as the addresses worth offering. */
  const eligibleAddresses: { current?: MaybeRefOrGetter<string[]> } = {};
  // The two params the pill bar writes. The real `airdropParams` wraps them in a params bag; here
  // they are handed back directly so a test can drive them the way the bar would.
  const selectedAddresses: { current?: Ref<string[]> } = {};
  const status: { current?: Ref<string> } = {};

  return {
    airdropsRef,
    eligibleAddresses,
    fetchAirdrops: vi.fn(async (): Promise<void> => {}),
    rememberSorting: vi.fn(),
    selectedAddresses,
    status,
  };
});

function captured<T>(slot: { current?: T }, name: string): T {
  if (slot.current === undefined)
    throw new Error(`${name} was never captured - mount the page first`);

  return slot.current;
}

vi.mock('@/modules/airdrops/use-airdrops', async () => {
  const { ref: refFn, shallowRef: shallowRefFn } = await import('vue');
  return {
    useAirdrops: (): { airdrops: Ref<Airdrops>; fetchAirdrops: typeof fetchAirdrops; loading: Ref<boolean> } => {
      airdropsRef.current = refFn<Airdrops>({});
      return { airdrops: airdropsRef.current, fetchAirdrops, loading: shallowRefFn(false) };
    },
  };
});

vi.mock('@/modules/airdrops/use-airdrop-fields', () => ({
  airdropParams: (addresses: Ref<string[]>, statusRef: Ref<string>): { value: unknown } => {
    selectedAddresses.current = addresses;
    status.current = statusRef;
    return { value: {} };
  },
  useAirdropFields: (eligible: MaybeRefOrGetter<string[]>): [] => {
    eligibleAddresses.current = eligible;
    return [];
  },
}));

vi.mock('@/modules/core/table/pill/composables/use-pill-bar-labels', () => ({
  usePillBarLabels: (): Record<string, never> => ({}),
}));

vi.mock('@/modules/core/table/use-remember-table-sorting', () => ({
  TableId: { AIRDROP: 'airdrop' },
  useRememberTableSorting: rememberSorting,
}));

function row(index: number): AirdropWithIndex {
  return { address: ADDRESS_A, amount: bigNumberify(1), index, source: `source-${index}` };
}

describe('pages/airdrops/useAirdropsPage', () => {
  // The composable registers an onMounted hook and a watcher, so a harness left mounted would
  // answer a later test.
  const mounted: VueWrapper[] = [];

  function setup(): ReturnType<typeof useAirdropsPage> {
    const { result, wrapper } = withSetup(() => useAirdropsPage());
    mounted.push(wrapper);
    return result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    while (mounted.length > 0)
      mounted.pop()?.unmount();
  });

  it('should fetch the airdrops on mount', async () => {
    setup();
    await flushPromises();

    expect(fetchAirdrops).toHaveBeenCalledTimes(1);
  });

  it('should derive the rows from the fetched airdrops', async () => {
    const { rows } = setup();
    await flushPromises();

    set(captured(airdropsRef, 'airdrops'), {
      [ADDRESS_A]: { uniswap: { amount: bigNumberify(4), asset: 'UNI', claimed: true, hasDecoder: true, link: 'l' } },
    });
    await nextTick();

    expect(get(rows)).toHaveLength(1);
    expect(get(rows)[0].source).toBe('uniswap');
  });

  it('should offer only the addresses that actually hold an airdrop as filter options', async () => {
    setup();
    await flushPromises();

    expect(toValue(captured(eligibleAddresses, 'eligible addresses'))).toEqual([]);

    set(captured(airdropsRef, 'airdrops'), {
      [ADDRESS_A]: { uniswap: { amount: bigNumberify(4), asset: 'UNI', claimed: true, link: 'l' } },
      [ADDRESS_B]: { cow: { amount: bigNumberify(1), asset: 'COW', claimed: false, link: 'l' } },
    });
    await nextTick();

    // Handed as a getter, so the list has to track a later fetch rather than being read once.
    expect(toValue(captured(eligibleAddresses, 'eligible addresses'))).toEqual([ADDRESS_A, ADDRESS_B]);
  });

  describe('the pagination reset', () => {
    it('should return to the first page when the status changes', async () => {
      const { modelPagination } = setup();
      await flushPromises();

      set(modelPagination, { limit: 10, page: 4, total: 100 });
      set(captured(status, 'status'), 'claimed');
      await nextTick();

      expect(get(modelPagination)?.page).toBe(1);
    });

    it('should return to the first page when the addresses change', async () => {
      const { modelPagination } = setup();
      await flushPromises();

      set(modelPagination, { limit: 10, page: 4, total: 100 });
      set(captured(selectedAddresses, 'selected addresses'), [ADDRESS_B]);
      await nextTick();

      expect(get(modelPagination)?.page).toBe(1);
    });

    it('should keep the rest of the pagination while resetting the page', async () => {
      const { modelPagination } = setup();
      await flushPromises();

      set(modelPagination, { limit: 25, page: 4, total: 100 });
      set(captured(status, 'status'), 'claimed');
      await nextTick();

      expect(get(modelPagination)?.limit).toBe(25);
      expect(get(modelPagination)?.total).toBe(100);
    });
  });

  describe('single expand', () => {
    it('should open a row', async () => {
      const { expand, modelExpanded } = setup();
      await flushPromises();

      const first = row(0);
      expand(first);

      expect(get(modelExpanded)).toEqual([first]);
    });

    it('should replace the open row rather than opening a second', async () => {
      const { expand, modelExpanded } = setup();
      await flushPromises();

      const first = row(0);
      const second = row(1);
      expand(first);
      expand(second);

      expect(get(modelExpanded)).toEqual([second]);
    });

    it('should close the row when it is clicked again', async () => {
      const { expand, modelExpanded } = setup();
      await flushPromises();

      const first = row(0);
      expand(first);
      expand(first);

      expect(get(modelExpanded)).toEqual([]);
    });
  });

  it('should register the table sorting under the airdrop table id', async () => {
    setup();
    await flushPromises();

    expect(rememberSorting).toHaveBeenCalledWith('airdrop', expect.anything(), expect.anything());
  });

  it('should remember the dismissed unknown-status alert across mounts', async () => {
    const { modelHideUnknownAlert } = setup();
    await flushPromises();

    set(modelHideUnknownAlert, true);
    await nextTick();

    expect(get(setup().modelHideUnknownAlert)).toBe(true);
  });
});
