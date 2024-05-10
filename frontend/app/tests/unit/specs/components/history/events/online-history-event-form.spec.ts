import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount,
} from '@vue/test-utils';
import { type Pinia, createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import flushPromises from 'flush-promises';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import OnlineHistoryEventForm from '@/components/history/events/forms/OnlineHistoryEventForm.vue';
import type { AssetMap } from '@/types/asset';
import type { OnlineHistoryEvent } from '@/types/history/events';

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

describe('onlineHistoryEventForm.vue', () => {
  setupDayjs();
  let wrapper: Wrapper<OnlineHistoryEventForm>;
  let pinia: Pinia;

  const asset = {
    name: 'Ethereum',
    symbol: 'ETH',
    assetType: 'own chain',
    isCustomAsset: false,
  };

  const mapping: AssetMap = {
    assetCollections: {},
    assets: { [asset.symbol]: asset },
  };

  const groupHeader: OnlineHistoryEvent = {
    identifier: 449,
    entryType: HistoryEventEntryType.HISTORY_EVENT,
    eventIdentifier: 'STJ6KRHJYGA',
    sequenceIndex: 20,
    timestamp: 1696741486185,
    location: 'kraken',
    asset: asset.symbol,
    balance: {
      amount: bigNumberify(10),
      usdValue: bigNumberify(40),
    },
    eventType: 'staking',
    eventSubtype: 'reward',
    locationLabel: 'Kraken 1',
    notes: 'History event notes',
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
    return mount(OnlineHistoryEventForm, {
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
        (
          wrapper.find('[data-cy=eventIdentifier] input')
            .element as HTMLInputElement
        ).value,
      ).toBe('');

      expect(
        (
          wrapper.find('[data-cy=locationLabel] .input-value')
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
        (
          wrapper.find('[data-cy=eventIdentifier] input')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.eventIdentifier);

      expect(
        (
          wrapper.find('[data-cy=locationLabel] .input-value')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.locationLabel);

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
        (
          wrapper.find('[data-cy=eventIdentifier] input')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.eventIdentifier);

      expect(
        (
          wrapper.find('[data-cy=locationLabel] .input-value')
            .element as HTMLInputElement
        ).value,
      ).toBe(groupHeader.locationLabel);

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

  it('should show correct eventSubtypes options, based on selected eventType', async () => {
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
});
