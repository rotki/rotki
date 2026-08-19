import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { TradableAsset } from '@/modules/wallet/types';
import { bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import TradeAssetSelector from '@/modules/wallet/send/TradeAssetSelector.vue';

const NAMES: Record<string, { symbol: string; name: string }> = {
  'ETH': { name: 'Ethereum', symbol: 'ETH' },
  'eip155:1/erc20:0xaaa': { name: 'Zeus Finance', symbol: 'ZEU' },
  'eip155:1/erc20:0xbbb': { name: 'AgentX', symbol: 'AGE' },
  'eip155:1/erc20:0xccc': { name: 'TrueUSD', symbol: 'TUSD' },
  'OP': { name: 'Optimism', symbol: 'OP' },
};

function tradable(identifier: string, chain: string): TradableAsset {
  return { amount: bigNumberify(1), asset: identifier, chain };
}

interface VirtualListStub {
  containerProps: { ref: Ref<HTMLElement | undefined>; style: Record<string, string> };
  list: ComputedRef<{ data: unknown; index: number }[]>;
  scrollTo: (index: number) => void;
  wrapperProps: ComputedRef<{ style: Record<string, string> }>;
}

const allOwnedAssets = ref<TradableAsset[]>([]);
const supportedChainsForConnectedAccount = ref<string[]>(['eth', 'optimism']);
const connected = ref<boolean>(true);
const connectedAddress = ref<string | undefined>('0xabc');
const virtualListArgs = vi.fn();
const virtualScrollTo = vi.fn();
const orchestratorDetect = vi.fn();

vi.mock('@/modules/wallet/use-wallet-store', () => ({
  useWalletStore: vi.fn(() => ({ connected, connectedAddress, supportedChainsForConnectedAccount })),
}));

vi.mock('@/modules/wallet/use-tradable-asset', () => ({
  useInjectedTradableAsset: vi.fn(() => ({
    allOwnedAssets,
    getAssetDetail: (): ComputedRef<undefined> => computed(() => undefined),
  })),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn(() => ({
    getAssetField: (identifier: string, field: string): string => {
      const entry = NAMES[identifier];
      if (!entry)
        return '';
      return field === 'symbol' ? entry.symbol : entry.name;
    },
    useAssetField: (): ComputedRef<string> => computed(() => ''),
  })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getEvmChainName: (chain: string): string => chain,
    getNativeAsset: (chain: string): string => (chain === 'eth' ? 'ETH' : 'OP'),
  })),
}));

vi.mock('@/modules/wallet/send/use-balance-queries', () => ({
  useBalanceQueries: vi.fn(() => ({ useQueryingBalances: ref(false), warnUntrackedAddress: ref(false) })),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: vi.fn(() => ({ useIsActive: (): Ref<boolean> => ref(false) })),
}));

vi.mock('@/modules/balances/blockchain/use-token-detection-orchestrator', () => ({
  useTokenDetectionOrchestrator: vi.fn(() => ({ detectTokens: orchestratorDetect })),
}));

// happy-dom reports every element as zero-height, so the real useVirtualList would render an empty
// window and no assertion about rows could distinguish "filtered out" from "scrolled out of view".
// The stub renders everything and records the windowing config, which is what this component owns.
vi.mock('@vueuse/core', async () => {
  const mod = await vi.importActual<typeof import('@vueuse/core')>('@vueuse/core');
  const { computed: vueComputed, shallowRef, toValue: vueToValue } = await import('vue');
  return {
    ...mod,
    useVirtualList: (source: MaybeRefOrGetter<unknown[]>, options: unknown): VirtualListStub => {
      virtualListArgs(options);
      return {
        // A real ref, not a computed: Vue writes the element into it and a computed is readonly.
        containerProps: { ref: shallowRef(), style: {} },
        list: vueComputed(() => vueToValue(source).map((data, index) => ({ data, index }))),
        scrollTo: virtualScrollTo,
        wrapperProps: vueComputed(() => ({ style: {} })),
      };
    },
  };
});

describe('tradeAssetSelector', () => {
  function createWrapper(props: Record<string, unknown> = {}): VueWrapper {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(TradeAssetSelector, {
      global: {
        plugins: [pinia],
        provide: libraryDefaults,
        stubs: {
          AssetDetails: true,
          // Drivable, so a test can widen the dialog to every chain and pick across one.
          ChainSelect: {
            emits: ['update:modelValue'],
            props: { modelValue: String },
            template: '<button data-testid="chain-select" @click="$emit(\'update:modelValue\', \'all\')" />',
          },
          // RuiDialog teleports to body, which puts its content outside the wrapper. This renders
          // the same slot inline so the dialog's contents can be queried.
          RuiDialog: {
            props: { modelValue: Boolean },
            template: '<div v-if="modelValue"><slot /></div>',
          },
        },
      },
      props: {
        address: '0xabc',
        amount: bigNumberify(1),
        chain: 'eth',
        modelValue: 'ETH',
        ...props,
      },
    });
  }

  async function openDialog(wrapper: VueWrapper): Promise<void> {
    await wrapper.find('[class*="rounded-b-lg"]').trigger('click');
    await flushPromises();
  }

  function optionKeys(wrapper: VueWrapper): string[] {
    return wrapper.findAll('[data-testid="trade-asset-option"]').map(node => node.attributes('data-key') ?? '');
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(supportedChainsForConnectedAccount, ['eth', 'optimism']);
    set(allOwnedAssets, [
      tradable('ETH', 'eth'),
      tradable('eip155:1/erc20:0xccc', 'eth'),
      tradable('eip155:1/erc20:0xbbb', 'eth'),
      tradable('eip155:1/erc20:0xaaa', 'eth'),
      tradable('OP', 'optimism'),
    ]);
  });

  it('should list the selected chain ordered native first then by symbol', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    expect(optionKeys(wrapper)).toEqual([
      'ETH',
      'eip155:1/erc20:0xbbb',
      'eip155:1/erc20:0xccc',
      'eip155:1/erc20:0xaaa',
    ]);
  });

  it('should render each option as a button so it is keyboard reachable', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    const options = wrapper.findAll('[data-testid="trade-asset-option"]');
    expect(options.length).toBeGreaterThan(0);
    options.forEach((option) => {
      expect(option.element.tagName).toBe('BUTTON');
      expect(option.attributes('type')).toBe('button');
    });
  });

  it('should scroll back to the top when the search narrows the list', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);
    virtualScrollTo.mockClear();

    await wrapper.find('[data-testid="trade-asset-search"]').setValue('agent');
    await flushPromises();

    expect(virtualScrollTo).toHaveBeenCalledWith(0);
  });

  it('should not scroll back to the top when the balances tick', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);
    virtualScrollTo.mockClear();

    // A balances refresh rebuilds the owned list into a new array with the same contents. Resetting
    // the scroll on that would yank the list from under a user who was scrolling it.
    set(allOwnedAssets, [...get(allOwnedAssets)]);
    await flushPromises();

    expect(virtualScrollTo).not.toHaveBeenCalled();
  });

  it('should hold one height whether the list is populated or empty', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    const populated = wrapper.find('[data-testid="trade-asset-option"]').element.parentElement?.parentElement;
    assert(populated);
    const populatedHeight = [...populated.classList].find(name => name.startsWith('h-['));

    await wrapper.find('[data-testid="trade-asset-search"]').setValue('zzzznomatch');
    await flushPromises();
    const emptyHeight = [...wrapper.find('[data-testid="trade-asset-empty"]').element.classList]
      .find(name => name.startsWith('h-['));

    // A `max-h` would size the dialog to the result count, so it would grow and collapse on every
    // keystroke. Both states must pin the same fixed height instead.
    expect(populatedHeight).toBeDefined();
    expect(emptyHeight).toBe(populatedHeight);
    expect(populated.className).not.toContain('max-h-');
  });

  it('should close from the header button without painting it white on white', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    const close = wrapper.find('[data-testid="trade-asset-close"]');
    // happy-dom computes no colours, so the guard is on the override that caused it: the icon sat
    // on the card's white header with `text-white`, which made it invisible in light mode.
    expect(close.html()).not.toContain('text-white');

    await close.trigger('click');
    await flushPromises();

    expect(wrapper.findAll('[data-testid="trade-asset-option"]')).toHaveLength(0);
  });

  it('should window the list rather than rendering every row', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    expect(virtualListArgs).toHaveBeenCalledWith(expect.objectContaining({ itemHeight: 56, overscan: 6 }));
  });

  it('should filter the options by the search box', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    await wrapper.find('[data-testid="trade-asset-search"]').setValue('agent');
    await flushPromises();

    expect(optionKeys(wrapper)).toEqual(['eip155:1/erc20:0xbbb']);
  });

  it('should show a search-specific empty message when nothing matches', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    await wrapper.find('[data-testid="trade-asset-search"]').setValue('zzzznomatch');
    await flushPromises();

    expect(optionKeys(wrapper)).toEqual([]);
    expect(wrapper.find('[data-testid="trade-asset-empty"]').text()).toContain('no_search_results');
  });

  it('should show the no-assets message when the chain owns nothing', async () => {
    set(allOwnedAssets, []);
    const wrapper = createWrapper();
    await openDialog(wrapper);

    expect(wrapper.find('[data-testid="trade-asset-empty"]').text()).toContain('no_assets_found');
  });

  it('should clear the search when the dialog closes', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);
    await wrapper.find('[data-testid="trade-asset-search"]').setValue('agent');
    await flushPromises();
    expect(optionKeys(wrapper)).toHaveLength(1);

    await wrapper.findAll('[data-testid="trade-asset-option"]')[0].trigger('click');
    await flushPromises();
    await openDialog(wrapper);

    expect(optionKeys(wrapper)).toHaveLength(4);
  });

  it('should emit the picked asset and close the dialog', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    await wrapper.findAll('[data-testid="trade-asset-option"]')[1].trigger('click');
    await flushPromises();

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['eip155:1/erc20:0xbbb']);
    expect(wrapper.findAll('[data-testid="trade-asset-option"]')).toHaveLength(0);
  });

  it('should list every supported chain and carry the chain across when "all" is picked', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    await wrapper.find('[data-testid="chain-select"]').trigger('click');
    await flushPromises();
    expect(optionKeys(wrapper)).toHaveLength(5);

    const optimism = wrapper.findAll('[data-testid="trade-asset-option"]')
      .find(option => option.attributes('data-key') === 'OP');
    assert(optimism);
    await optimism.trigger('click');
    await flushPromises();

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['OP']);
    expect(wrapper.emitted('update:chain')?.at(-1)).toEqual(['optimism']);
  });

  it('should clear the search box with the clear button', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);
    await wrapper.find('[data-testid="trade-asset-search"]').setValue('agent');
    await flushPromises();

    await wrapper.find('[data-testid="trade-asset-search-clear"]').trigger('click');
    await flushPromises();

    expect(optionKeys(wrapper)).toHaveLength(4);
  });

  it('should replace a selection that the chain does not own', async () => {
    const wrapper = createWrapper({ chain: 'optimism', modelValue: 'ETH' });
    await flushPromises();

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['OP']);
  });

  it('should keep a selection the chain does own', async () => {
    const wrapper = createWrapper({ chain: 'eth', modelValue: 'eip155:1/erc20:0xaaa' });
    await flushPromises();

    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should not clear the selection when the chain owns nothing', async () => {
    set(allOwnedAssets, [tradable('ETH', 'eth')]);
    const wrapper = createWrapper({ chain: 'optimism', modelValue: 'ETH' });
    await flushPromises();

    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });
});
