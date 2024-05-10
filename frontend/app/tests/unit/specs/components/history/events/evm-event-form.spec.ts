import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount,
} from '@vue/test-utils';
import { type Pinia, createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import flushPromises from 'flush-promises';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import EvmEventForm from '@/components/history/events/forms/EvmEventForm.vue';
import type { AssetMap } from '@/types/asset';
import type { EvmHistoryEvent } from '@/types/history/events';

vi.mock('json-editor-vue', () => ({
  template: '<input />',
}));

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

describe('evmEventForm.vue', () => {
  setupDayjs();
  let wrapper: Wrapper<EvmEventForm>;
  let pinia: Pinia;

  const asset = {
    name: 'Ethereum',
    symbol: 'eip155:1/erc20:0xA3Ee8CEB67906492287FFD256A9422313B5796d4',
    assetType: 'own chain',
    isCustomAsset: false,
  };

  const mapping: AssetMap = {
    assetCollections: {},
    assets: { [asset.symbol]: asset },
  };

  const groupHeader: EvmHistoryEvent = {
    identifier: 14344,
    eventIdentifier:
      '10x4ba949779d936631dc9eb68fa9308c18de51db253aeea919384c728942f95ba9',
    sequenceIndex: 2411,
    timestamp: 1686495083,
    location: 'ethereum',
    asset: asset.symbol,
    balance: {
      amount: bigNumberify(610),
      usdValue: bigNumberify(0),
    },
    eventType: 'receive',
    eventSubtype: '',
    locationLabel: '0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8',
    notes:
      'Receive 610 Visit https://rafts.cc to claim rewards. from 0x30a2EBF10f34c6C4874b0bDD5740690fD2f3B70C to 0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8',
    entryType: HistoryEventEntryType.EVM_EVENT,
    address: '0x30a2EBF10f34c6C4874b0bDD5740690fD2f3B70C',
    counterparty: null,
    product: null,
    txHash: '0x4ba949779d936631dc9eb68fa9308c18de51db253aeea919384c728942f95ba9',
  };

  beforeEach(() => {
    vi.useFakeTimers();
    pinia = createPinia();
    setActivePinia(pinia);
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    vi.mocked(useBalancePricesStore().getHistoricPrice).mockResolvedValue(One);
  });

  const createWrapper = (options: ThisTypedMountOptions<any> = {}) => {
    const vuetify = new Vuetify();
    return mount(EvmEventForm, {
      pinia,
      vuetify,
      ...options,
    });
  };

  describe('should prefill the fields based on the props', () => {
    it('no `groupHeader`, `editableItem`, nor `nextSequence` are passed', async () => {
      wrapper = createWrapper();
      await nextTick();

      expect(
        (wrapper.find('[data-cy=txHash] input').element as HTMLInputElement)
          .value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=locationLabel] .input-value')
            .element as HTMLInputElement
        ).value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=address] .input-value')
            .element as HTMLInputElement
        ).value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=sequenceIndex] input')
            .element as HTMLInputElement
        ).value,
      ).toBe('');
    });

    it('`groupHeader` and `nextSequence` are passed', async () => {
      wrapper = createWrapper();
      await nextTick();
      await wrapper.setProps({ groupHeader, nextSequence: '10' });

      expect(
        (wrapper.find('[data-cy=txHash] input').element as HTMLInputElement)
          .value,
      ).toBe(groupHeader.txHash);

      expect(
        (
          wrapper.find('[data-cy=locationLabel] .input-value')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.locationLabel);

      expect(
        (
          wrapper.find('[data-cy=address] .input-value')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.address);

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=sequenceIndex] input')
            .element as HTMLInputElement
        ).value,
      ).toBe('10');

      expect(
        (
          wrapper.find('[data-cy=notes] textarea:not([aria-hidden="true"])')
            .element as HTMLTextAreaElement
        ).value,
      ).toBe('');
    });

    it('`groupHeader`, `editableItem`, and `nextSequence` are passed', async () => {
      wrapper = createWrapper();
      await nextTick();
      await wrapper.setProps({ groupHeader, editableItem: groupHeader, nextSequence: '10' });

      expect(
        (wrapper.find('[data-cy=txHash] input').element as HTMLInputElement)
          .value,
      ).toBe(groupHeader.txHash);

      expect(
        (
          wrapper.find('[data-cy=locationLabel] .input-value')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.locationLabel);

      expect(
        (
          wrapper.find('[data-cy=address] .input-value')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.address);

      expect(
        (wrapper.find('[data-cy=amount] input').element as HTMLInputElement)
          .value,
      ).toBe(groupHeader.balance.amount.toString());

      expect(
        (
          wrapper.find('[data-cy=sequenceIndex] input')
            .element as HTMLInputElement
        ).value.replace(',', ''),
      ).toBe(groupHeader.sequenceIndex.toString());

      expect(
        (
          wrapper.find('[data-cy=notes] textarea:not([aria-hidden="true"])')
            .element as HTMLTextAreaElement
        ).value,
      ).toBe(groupHeader.notes);
    });
  });

  it('should show all eventTypes options correctly', async () => {
    wrapper = createWrapper({ propsData: { groupHeader } });
    await nextTick();
    await flushPromises();

    const { historyEventTypesData } = useHistoryEventMappings();

    expect(
      wrapper.findAll('[data-cy=eventType] .selections span'),
    ).toHaveLength(get(historyEventTypesData).length);
  });

  it('should show all eventSubTypes options correctly', async () => {
    wrapper = createWrapper({ propsData: { groupHeader } });
    await nextTick();
    await flushPromises();

    const { historyEventSubTypesData } = useHistoryEventMappings();

    expect(
      wrapper.findAll('[data-cy=eventSubtype] .selections span'),
    ).toHaveLength(get(historyEventSubTypesData).length);
  });

  it('should show all counterparties options correctly', async () => {
    wrapper = createWrapper({ propsData: { groupHeader } });
    await nextTick();
    await flushPromises();

    const { counterparties } = useHistoryEventCounterpartyMappings();

    expect(
      wrapper.findAll('[data-cy=counterparty] .selections span'),
    ).toHaveLength(get(counterparties).length);
  });

  it('should show correct eventSubtypes options, based on selected eventType and counterparty', async () => {
    wrapper = createWrapper({ propsData: { groupHeader } });
    await nextTick();
    await flushPromises();

    const { historyEventTypeGlobalMapping } = useHistoryEventMappings();

    const selectedEventType = 'deposit';

    await wrapper.find('[data-cy=eventType] .input-value').trigger('input', {
      value: selectedEventType,
    });

    await nextTick();

    const keysFromGlobalMappings = Object.keys(
      get(historyEventTypeGlobalMapping)?.[selectedEventType] ?? {},
    );

    const spans = wrapper.findAll(
      '[data-cy=eventSubtype] .selections span',
    );
    expect(spans).toHaveLength(keysFromGlobalMappings.length);

    for (let i = 0; i < keysFromGlobalMappings.length; i++)
      expect(keysFromGlobalMappings.includes(spans.at(i).text())).toBeTruthy();
  });

  it('should show product options, based on selected counterparty', async () => {
    wrapper = createWrapper({ propsData: { groupHeader } });
    await nextTick();
    await flushPromises();

    expect(wrapper.find('[data-cy=product]').attributes('disabled')).toBe(
      'disabled',
    );

    // input is still disabled, if the counterparty doesn't have mapped products.
    await wrapper.find('[data-cy=counterparty] .input-value').trigger('input', {
      value: '1inch',
    });
    await nextTick();

    expect(wrapper.find('[data-cy=product]').attributes('disabled')).toBe(
      'disabled',
    );

    // products options should be showed correctly, if the counterparty have mapped products.
    const selectedCounterparty = 'convex';
    await wrapper.find('[data-cy=counterparty] .input-value').trigger('input', {
      value: selectedCounterparty,
    });
    await nextTick();

    const { historyEventProductsMapping } = useHistoryEventProductMappings();

    const products = get(historyEventProductsMapping)[selectedCounterparty];

    const spans = wrapper.findAll('[data-cy=product] .selections span');
    expect(spans).toHaveLength(products.length);

    for (let i = 0; i < products.length; i++)
      expect(products.includes(spans.at(i).text())).toBeTruthy();
  });
});
