import type { Collection } from '@/modules/core/common/collection';
import { type BigNumber, bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import NewlyDetectedAssetRowActions from '@/modules/assets/detection/NewlyDetectedAssetRowActions.vue';
import NewlyDetectedAssetTable from '@/modules/assets/detection/NewlyDetectedAssetTable.vue';
import NewlyDetectedAssetToolbar from '@/modules/assets/detection/NewlyDetectedAssetToolbar.vue';
import { type NewDetectedToken, NewDetectedTokenKind } from '@/modules/assets/detection/types';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { held, spies } = vi.hoisted(() => {
  const held: { rows: NewDetectedToken[]; ready?: Ref<boolean> } = { rows: [] };
  return {
    held,
    spies: {
      getAssetPrice: vi.fn<(asset: string) => BigNumber | undefined>(),
      markAsSpam: vi.fn<(identifiers?: string | string[]) => Promise<void>>(),
      refetch: vi.fn<() => Promise<void>>(),
      removeTokens: vi.fn<(identifiers?: string | string[]) => Promise<void>>(),
      toggleSelection: vi.fn<() => Promise<void>>(),
    },
  };
});

vi.mock('@/modules/assets/detection/use-newly-detected-tokens', () => ({
  useNewlyDetectedTokens: (): object => ({ getData: vi.fn(), isReady: held.ready }),
}));

vi.mock('@/modules/core/table/use-server-table', () => ({
  useServerTable: (): object => ({
    collection: ref<Collection<NewDetectedToken>>({
      data: held.rows,
      found: held.rows.length,
      limit: -1,
      total: held.rows.length,
      totalValue: undefined,
    }),
    error: ref<string>(),
    filter: ref<Record<string, string>>({}),
    isLoading: ref<boolean>(false),
    pagination: ref({ limit: 10, page: 1, total: held.rows.length }),
    refetch: spies.refetch,
    sort: ref([]),
  }),
}));

vi.mock('@/modules/assets/detection/use-newly-detected-selection', () => ({
  useNewlyDetectedSelection: (): object => ({
    allSelected: computed<boolean>(() => false),
    markAsSpam: spies.markAsSpam,
    modelSelected: ref<string[]>([]),
    removeTokens: spies.removeTokens,
    toggleSelection: spies.toggleSelection,
  }),
}));

vi.mock('@/modules/assets/prices/use-price-utils', () => ({
  usePriceUtils: (): object => ({ getAssetPrice: spies.getAssetPrice }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({
    allEvmChains: ref([{ evmChainName: 'optimism', id: 10, name: 'optimism' }]),
  }),
}));

const EVM_ADDRESS = '0x4200000000000000000000000000000000000042';
const SOLANA_ADDRESS = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';

const EVM_TOKEN: NewDetectedToken = {
  detectedAt: 1_700_000_000_000,
  tokenIdentifier: `eip155:10/erc20:${EVM_ADDRESS}`,
  tokenKind: NewDetectedTokenKind.EVM,
};

const SOLANA_TOKEN: NewDetectedToken = {
  detectedAt: 1_700_000_000_000,
  tokenIdentifier: `solana:${SOLANA_ADDRESS}`,
  tokenKind: NewDetectedTokenKind.SOLANA,
};

describe('newlyDetectedAssetTable', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof NewlyDetectedAssetTable>>;

  function createWrapper(): VueWrapper<InstanceType<typeof NewlyDetectedAssetTable>> {
    return mount(NewlyDetectedAssetTable, {
      global: {
        plugins: [pinia],
        stubs: {
          AssetDetails: true,
          DateDisplay: true,
          FiatDisplay: true,
          HashLink: true,
          NewlyDetectedAssetRowActions: true,
          NewlyDetectedAssetToolbar: true,
          RuiCard: { template: '<div><slot name="custom-header" /><slot /></div>' },
          RuiDataTable: {
            props: ['rows'],
            template: `<div>
              <div v-for="row in rows" :key="row.tokenIdentifier">
                <slot name="item.address" :row="row" />
                <slot name="item.price" :row="row" />
                <slot name="item.actions" :row="row" />
              </div>
            </div>`,
          },
          TablePageLayout: { template: '<div><slot /></div>' },
        },
      },
    });
  }

  async function mountWith(rows: NewDetectedToken[]): Promise<void> {
    held.rows = rows;
    wrapper = createWrapper();
    await flushPromises();
  }

  beforeEach(() => {
    vi.clearAllMocks();
    pinia = createCustomPinia();
    setActivePinia(pinia);
    held.rows = [];
    held.ready = ref<boolean>(false);
    spies.refetch.mockResolvedValue(undefined);
    spies.getAssetPrice.mockReturnValue(undefined);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  describe('loading', () => {
    it('should load the detected tokens when it opens', async () => {
      await mountWith([]);

      expect(spies.refetch).toHaveBeenCalledOnce();
    });

    it('should load them again once the token store is ready', async () => {
      await mountWith([]);
      spies.refetch.mockClear();

      assert(held.ready);
      set(held.ready, true);
      await nextTick();

      expect(spies.refetch).toHaveBeenCalledOnce();
    });
  });

  describe('rows', () => {
    it('should link an evm token by its contract address on its chain', async () => {
      await mountWith([EVM_TOKEN]);

      expect(wrapper.findComponent(HashLink).props()).toMatchObject({ location: 'optimism', text: EVM_ADDRESS });
    });

    it('should link a solana token by its mint address on solana', async () => {
      await mountWith([SOLANA_TOKEN]);

      expect(wrapper.findComponent(HashLink).props()).toMatchObject({ location: 'solana', text: SOLANA_ADDRESS });
    });

    it('should show the price known for the token', async () => {
      spies.getAssetPrice.mockReturnValue(bigNumberify('1.23'));

      await mountWith([EVM_TOKEN]);

      expect(spies.getAssetPrice).toHaveBeenCalledWith(EVM_TOKEN.tokenIdentifier);
      expect(wrapper.findComponent(FiatDisplay).props('value')).toEqual(bigNumberify('1.23'));
    });
  });

  describe('actions', () => {
    it('should accept or mark as spam just the token of a row', async () => {
      await mountWith([EVM_TOKEN, SOLANA_TOKEN]);
      const [, solanaRow] = wrapper.findAllComponents(NewlyDetectedAssetRowActions);

      solanaRow.vm.$emit('accept');
      solanaRow.vm.$emit('mark-spam');

      expect(spies.removeTokens).toHaveBeenCalledExactlyOnceWith(SOLANA_TOKEN.tokenIdentifier);
      expect(spies.markAsSpam).toHaveBeenCalledExactlyOnceWith(SOLANA_TOKEN.tokenIdentifier);
    });

    it('should apply the toolbar actions to the selection', async () => {
      await mountWith([EVM_TOKEN]);
      const toolbar = wrapper.findComponent(NewlyDetectedAssetToolbar);

      toolbar.vm.$emit('accept');
      toolbar.vm.$emit('mark-spam');
      toolbar.vm.$emit('toggle-selection');

      expect(spies.removeTokens).toHaveBeenCalledExactlyOnceWith();
      expect(spies.markAsSpam).toHaveBeenCalledExactlyOnceWith();
      expect(spies.toggleSelection).toHaveBeenCalledOnce();
    });
  });
});
