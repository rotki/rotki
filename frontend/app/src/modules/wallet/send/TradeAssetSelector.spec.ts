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

const getAssetField = vi.fn<(identifier: string, field: string) => string>();

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn(() => ({
    getAssetField,
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
    const wrapper = mount(TradeAssetSelector, {
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
    return wrapper;
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
    getAssetField.mockImplementation((identifier: string, field: string) => {
      const entry = NAMES[identifier];
      if (!entry)
        return '';
      return field === 'symbol' ? entry.symbol : entry.name;
    });
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

    expect(populatedHeight).toBeDefined();
    expect(emptyHeight).toBe(populatedHeight);
    expect(populated.className).not.toContain('max-h-');
  });

  it('should close from the header button without painting it white on white', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    const close = wrapper.find('[data-testid="trade-asset-close"]');
    expect(close.html()).not.toContain('text-white');

    await close.trigger('click');
    await flushPromises();

    expect(wrapper.findAll('[data-testid="trade-asset-option"]')).toHaveLength(0);
  });

  it('should pick the highlighted row with the keyboard', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    const field = wrapper.find('[data-testid="trade-asset-search"]');
    await field.trigger('keydown', { key: 'ArrowDown' });
    await field.trigger('keydown', { key: 'Enter' });
    await flushPromises();

    // Second row of ETH, AGE, TUSD, ZEU.
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['eip155:1/erc20:0xbbb']);
  });

  it('should let a search be committed with enter alone', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    const field = wrapper.find('[data-testid="trade-asset-search"]');
    await field.setValue('true');
    await flushPromises();
    await field.trigger('keydown', { key: 'Enter' });
    await flushPromises();

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['eip155:1/erc20:0xccc']);
  });

  it('should close on escape from the search field', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    await wrapper.find('[data-testid="trade-asset-search"]').trigger('keydown', { key: 'Escape' });
    await flushPromises();

    expect(wrapper.findAll('[data-testid="trade-asset-option"]')).toHaveLength(0);
  });

  it('should open highlighted on the current selection', async () => {
    const wrapper = createWrapper({ modelValue: 'eip155:1/erc20:0xaaa' });
    await openDialog(wrapper);

    const indexAmongEthAgeTusdZeu = 3;
    expect(virtualScrollTo).toHaveBeenCalledWith(indexAmongEthAgeTusdZeu);
  });

  it('should mark the selected row', async () => {
    const wrapper = createWrapper({ modelValue: 'eip155:1/erc20:0xaaa' });
    await openDialog(wrapper);

    const selected = wrapper.findAll('[data-testid="trade-asset-option"]')
      .filter(node => node.attributes('aria-selected') === 'true');
    expect(selected).toHaveLength(1);
    expect(selected[0].attributes('data-key')).toBe('eip155:1/erc20:0xaaa');
  });

  it('should tick only the selected chain when an identifier spans chains', async () => {
    set(allOwnedAssets, [tradable('ETH', 'eth'), tradable('ETH', 'optimism')]);
    set(supportedChainsForConnectedAccount, ['eth', 'optimism']);
    const wrapper = createWrapper({ chain: 'optimism', modelValue: 'ETH' });
    await openDialog(wrapper);
    await wrapper.find('[data-testid="chain-select"]').trigger('click');
    await flushPromises();

    const ticked = wrapper.findAll('[data-testid="trade-asset-option"]')
      .filter(node => node.attributes('aria-selected') === 'true');
    expect(ticked).toHaveLength(1);
    expect(ticked[0].attributes('data-chain')).toBe('optimism');
  });

  it('should not resolve any asset name before the dialog is opened', () => {
    createWrapper();

    expect(getAssetField).not.toHaveBeenCalled();
  });

  it('should resolve names once the dialog opens', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    expect(getAssetField).toHaveBeenCalled();
  });

  it('should point the search field at the highlighted row for assistive tech', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    const field = wrapper.find('[data-testid="trade-asset-search"]');
    await field.trigger('keydown', { key: 'ArrowDown' });
    await flushPromises();

    const active = field.attributes('aria-activedescendant');
    expect(active).toBe('trade-asset-option-1');
    expect(wrapper.find(`#${active}`).exists()).toBe(true);
  });

  it('should report how many assets the chain holds', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    expect(wrapper.find('[data-testid="trade-asset-count"]').text()).toContain('4');
  });

  it('should report the narrowed count against the total while searching', async () => {
    const wrapper = createWrapper();
    await openDialog(wrapper);

    await wrapper.find('[data-testid="trade-asset-search"]').setValue('agent');
    await flushPromises();

    const text = wrapper.find('[data-testid="trade-asset-count"]').text();
    expect(text).toContain('1');
    expect(text).toContain('4');
  });

  it('should default to the head of the display order rather than the raw owned list', async () => {
    set(allOwnedAssets, [
      tradable('eip155:1/erc20:0xccc', 'eth'),
      tradable('ETH', 'eth'),
      tradable('eip155:1/erc20:0xaaa', 'eth'),
    ]);
    const wrapper = createWrapper({ modelValue: '' });
    await flushPromises();

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['ETH']);
  });

  it('should never default to a collectible', async () => {
    set(allOwnedAssets, [
      tradable('eip155:1/erc721:0xC0a302e6Ad8EcCC4d7A6c1514F8671D6B79269c7/104', 'eth'),
      tradable('eip155:1/erc20:0xccc', 'eth'),
    ]);
    const wrapper = createWrapper({ modelValue: '' });
    await flushPromises();

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['eip155:1/erc20:0xccc']);
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
