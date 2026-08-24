import type { AssetMap } from '@/modules/assets/types';
import type { TradeLocationData } from '@/modules/core/common/location';
import type { BitcoinEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { selectorContract } from '@test/utils/selector-contract';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { setupDayjs } from '@/modules/core/common/data/date';
import { useLocations } from '@/modules/core/common/use-locations';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';
import BitcoinEventForm from '@/modules/history/management/forms/BitcoinEventForm.vue';

vi.mock('json-editor-vue', () => ({
  template: '<input />',
}));

vi.mock('@/modules/history/events/use-history-events', () => ({
  useHistoryEvents: vi.fn(),
}));

vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: vi.fn(),
}));

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: vi.fn(),
}));

vi.mock('@/modules/history/events/mapping/use-history-event-counterparty-mappings', () => ({
  useHistoryEventCounterpartyMappings: vi.fn(),
}));

describe('forms/BitcoinEventForm.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof BitcoinEventForm>>;
  let addHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>>;
  let editHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>>;
  let addHistoricalPriceMock: ReturnType<typeof vi.fn<ReturnType<typeof useAssetPricesApi>['addHistoricalPrice']>>;
  let pinia: Pinia;

  const asset = {
    assetType: 'own chain',
    isCustomAsset: false,
    name: 'Bitcoin',
    symbol: 'BTC',
  };

  const mapping: AssetMap = {
    assetCollections: {},
    assets: { [asset.symbol]: asset },
  };

  const group: BitcoinEvent = {
    address: null,
    amount: bigNumberify(100),
    asset: asset.symbol,
    counterparty: null,
    entryType: HistoryEventEntryType.BITCOIN_EVENT,
    eventSubtype: '',
    eventType: 'receive',
    groupIdentifier: 'btc_e47f43692083b6b4bb3d4d6150acd3c016b09fb841e4055e1f5bb8ad44858bc6',
    identifier: 14344,
    location: 'bitcoin',
    locationLabel: 'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4',
    sequenceIndex: 2411,
    timestamp: 1686495083,
    txRef: 'e47f43692083b6b4bb3d4d6150acd3c016b09fb841e4055e1f5bb8ad44858bc6',
    userNotes: 'Receive 100 BTC from 1G3MiaKdccQmiTr4gYSKmrCVDaLQ5nvBRp',
  };

  beforeAll(() => {
    setupDayjs();
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    vi.useFakeTimers();
    addHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>();
    editHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>();
    addHistoricalPriceMock = vi.fn<ReturnType<typeof useAssetPricesApi>['addHistoricalPrice']>();
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    vi.mocked(useLocations).mockReturnValue(createMock<ReturnType<typeof useLocations>>({
      tradeLocations: computed<TradeLocationData[]>(() => [{
        identifier: 'bitcoin',
        name: 'Bitcoin',
      }, {
        identifier: 'bitcoin_cash',
        name: 'Bitcoin Cash',
      }]),
    }));
    vi.mocked(useHistoryEvents).mockReturnValue(createMock<ReturnType<typeof useHistoryEvents>>({
      addHistoryEvent: addHistoryEventMock,
      editHistoryEvent: editHistoryEventMock,
    }));
    vi.mocked(useAssetPricesApi).mockReturnValue(createMock<ReturnType<typeof useAssetPricesApi>>({
      addHistoricalPrice: addHistoricalPriceMock,
    }));
    vi.mocked(useHistoryEventCounterpartyMappings).mockReturnValue(createMock<ReturnType<typeof useHistoryEventCounterpartyMappings>>({
      counterparties: computed<string[]>(() => [
        'test-counterparty',
        'uniswap',
      ]),
    }));
  });

  afterEach(() => {
    wrapper.unmount();
    vi.useRealTimers();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof BitcoinEventForm> = {
    props: {
      data: { nextSequenceId: '0', type: 'add' },
    },
  }): VueWrapper<InstanceType<typeof BitcoinEventForm>> =>
    mount(BitcoinEventForm, {
      global: {
        plugins: [pinia],
        stubs: {
          I18nT: true,
        },
      },
      ...options,
    });

  it('should render the documented e2e selector contract', () => {
    wrapper = createWrapper();
    // The e2e suite finds every field through these selectors; losing one is an e2e break.
    expect(selectorContract(wrapper)).toMatchInlineSnapshot(`
      [
        "data-testid=amount",
        "data-testid=asset",
        "data-testid=bitcoin-event-form-advance",
        "data-testid=counterparty",
        "data-testid=datetime",
        "data-testid=event-action-picker",
        "data-testid=group-identifier",
        "data-testid=grouped-amount-input-swap",
        "data-testid=location",
        "data-testid=notes",
        "data-testid=primary",
        "data-testid=secondary",
        "data-testid=sequence-index",
        "data-testid=tx-ref",
      ]
    `);
  });

  it('should show the default state when opening the form without any data', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const txRefInput = wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input');
    const locationInput = wrapper.find<HTMLInputElement>('[data-testid=location] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');

    expect(txRefInput.element.value).toBe('');
    expect(locationInput.element.value).toBe('bitcoin');
    expect(sequenceIndexInput.element.value).toBe('0');
  });

  it('should update the proper fields adding an event to a group', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { group, nextSequenceId: '10', type: 'group-add' } });

    const txRefInput = wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input');
    const amountInput = wrapper.find<HTMLInputElement>('[data-testid=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');
    const noteTextArea = wrapper.find<HTMLTextAreaElement>('[data-testid=notes] textarea:not([aria-hidden="true"])');

    expect(txRefInput.element.value).toBe(group.txRef);
    expect(amountInput.element.value).toBe('0');
    expect(sequenceIndexInput.element.value).toBe('10');
    expect(noteTextArea.element.value).toBe('');
  });

  it('should update the fields when editing an event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { event: group, nextSequenceId: '10', type: 'edit' } });

    const txRefInput = wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input');
    const amountInput = wrapper.find<HTMLInputElement>('[data-testid=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');
    const notesTextArea = wrapper.find<HTMLTextAreaElement>('[data-testid=notes] textarea:not([aria-hidden="true"])');

    expect(txRefInput.element.value).toBe(group.txRef);
    expect(amountInput.element.value).toBe(group.amount.toString());
    expect(sequenceIndexInput.element.value.replace(',', '')).toBe(group.sequenceIndex.toString());
    expect(notesTextArea.element.value).toBe(group.userNotes);
  });

  it('should lock the location to the saved transaction outside the add flow', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    // the location picks the asset, so leaving it editable would let a BTC event that
    // belongs to a saved bitcoin transaction be relabelled as BCH, and vice versa
    expect(wrapper.find('[data-testid=location] input').attributes('disabled')).toBeUndefined();

    for (const data of [
      { event: group, nextSequenceId: '10', type: 'edit' },
      { group, nextSequenceId: '10', type: 'group-add' },
    ] as const) {
      await wrapper.setProps({ data });
      await vi.advanceTimersToNextTimerAsync();

      expect(wrapper.find('[data-testid=location] input').attributes('disabled')).toBeDefined();
      expect(wrapper.find('[data-testid=tx-ref] input').attributes('disabled')).toBeDefined();
    }
  });

  it('should show all counterparties options correctly', async () => {
    wrapper = createWrapper({ props: { data: { group, nextSequenceId: '1', type: 'group-add' } } });
    await vi.advanceTimersToNextTimerAsync();

    const { counterparties } = useHistoryEventCounterpartyMappings();

    expect(wrapper.findAll('[data-testid=counterparty] .selections span')).toHaveLength(get(counterparties).length);
  });

  it('should add a new bitcoin event when form is submitted', async () => {
    wrapper = createWrapper();
    await nextTick();
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-testid=tx-ref] input').setValue(group.txRef);
    await wrapper.find('[data-testid=location] input').setValue(group.location);
    wrapper.findComponent({ name: 'HistoryEventActionPicker' }).vm.$emit('update:modelValue', {
      eventSubtype: group.eventSubtype || 'none',
      eventType: group.eventType,
    });
    await nextTick();
    // the asset is not picked, it follows the location
    await wrapper.find('[data-testid=amount] input').setValue('100');
    await wrapper.find('[data-testid=sequence-index] input').setValue(group.sequenceIndex);
    await wrapper.find('[data-testid=notes] textarea:not([aria-hidden="true"])').setValue(group.userNotes);
    await wrapper.find('[data-testid=datetime] input').setValue(dayjs(group.timestamp).format('DD/MM/YYYY HH:mm:ss.SSS'));

    // group.counterparty is null, so no counterparty field to set
    // group.eventSubtype is '', so no eventSubtype field to set

    const saveMethod = wrapper.vm.save;

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(addHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(addHistoryEventMock).toHaveBeenCalledWith({
      amount: group.amount,
      asset: group.asset,
      counterparty: '',
      entryType: HistoryEventEntryType.BITCOIN_EVENT,
      eventSubtype: 'none',
      eventType: group.eventType,
      extraData: {},
      groupIdentifier: null,
      location: group.location,
      locationLabel: null,
      sequenceIndex: group.sequenceIndex.toString(),
      timestamp: group.timestamp,
      txRef: group.txRef,
      userNotes: group.userNotes,
    });
  });

  it('should not call editHistoryEvent when only updating the historic price', async () => {
    wrapper = createWrapper({
      props: {
        data: {
          event: group,
          nextSequenceId: '1',
          type: 'edit',
        },
      },
    });
    await vi.advanceTimersToNextTimerAsync();
    const saveMethod = wrapper.vm.save;

    // click save without changing anything
    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoricalPriceMock.mockResolvedValueOnce(true);

    await saveMethod();
    await nextTick();
    expect(editHistoryEventMock).not.toHaveBeenCalled();

    // click save after changing the historic price
    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    await wrapper.find('[data-testid=primary] input').setValue('1000');

    await saveMethod();
    await nextTick();
    expect(editHistoryEventMock).not.toHaveBeenCalled();
  });

  it('should edit an existing bitcoin event when form is submitted', async () => {
    wrapper = createWrapper({
      props: {
        data: {
          event: group,
          nextSequenceId: '1',
          type: 'edit',
        },
      },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-testid=amount] input').setValue('150');
    await wrapper.find('[data-testid=sequence-index] input').setValue('2111');
    await wrapper.find('[data-testid=notes] textarea:not([aria-hidden="true"])').setValue('user note');

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(editHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(editHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify('150'),
      asset: group.asset,
      counterparty: '',
      entryType: HistoryEventEntryType.BITCOIN_EVENT,
      eventSubtype: 'none',
      eventType: group.eventType,
      extraData: {},
      groupIdentifier: group.groupIdentifier,
      identifier: group.identifier,
      location: group.location,
      locationLabel: group.locationLabel ?? null,
      sequenceIndex: '2111',
      timestamp: group.timestamp,
      txRef: group.txRef,
      userNotes: 'user note',
    });
  });

  it('should keep the location and asset of the edited event', async () => {
    wrapper = createWrapper({
      props: {
        data: {
          event: {
            ...group,
            asset: 'BCH',
            groupIdentifier: `bch_${group.txRef}`,
            location: 'bitcoin_cash',
          },
          nextSequenceId: '1',
          type: 'edit',
        },
      },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-testid=amount] input').setValue('150');

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    expect(await wrapper.vm.save()).toBe(true);
    expect(editHistoryEventMock).toHaveBeenCalledWith(expect.objectContaining({
      asset: 'BCH',
      location: 'bitcoin_cash',
    }));
  });

  it('should handle server validation errors', async () => {
    wrapper = createWrapper({
      props: {
        data: {
          event: group,
          nextSequenceId: '1',
          type: 'edit',
        },
      },
    });
    await vi.advanceTimersToNextTimerAsync();

    // Change a field to make the form dirty
    await wrapper.find('[data-testid=amount] input').setValue('200');

    editHistoryEventMock.mockResolvedValueOnce({
      message: { amount: ['amount too large'] },
      success: false,
    });

    const saveMethod = wrapper.vm.save;

    const saveResult = await saveMethod();
    await nextTick();

    expect(editHistoryEventMock).toHaveBeenCalled();
    expect(saveResult).toBe(false);
    expect(wrapper.find('[data-testid=amount] .details').text()).toBe('amount too large');
  });

  it('should display validation errors when the form is invalid', async () => {
    wrapper = createWrapper();
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-testid=amount] .details').exists()).toBe(true);
    // the asset field has nothing to validate since it follows the location
    expect(wrapper.find('[data-testid=tx-ref] .details').exists()).toBe(true);
  });

  describe('actualGroupIdentifier', () => {
    const eventWithActualGroupIdentifier: BitcoinEvent = {
      ...group,
      actualGroupIdentifier: 'ACTUAL123',
      groupIdentifier: 'LINKED456',
    };

    it('should use actualGroupIdentifier when present and disable the field', async () => {
      wrapper = createWrapper({
        props: { data: { event: eventWithActualGroupIdentifier, nextSequenceId: '1', type: 'edit' } },
      });
      await vi.advanceTimersToNextTimerAsync();

      await wrapper.find('[data-testid=bitcoin-event-form-advance] [data-accordion-trigger]').trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
      expect(groupIdentifierInput.element.value).toBe('ACTUAL123');
      expect(groupIdentifierInput.element.disabled).toBe(true);
    });

    it('should use groupIdentifier when actualGroupIdentifier is not present', async () => {
      wrapper = createWrapper({
        props: { data: { event: group, nextSequenceId: '1', type: 'edit' } },
      });
      await vi.advanceTimersToNextTimerAsync();

      await wrapper.find('[data-testid=bitcoin-event-form-advance] [data-accordion-trigger]').trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
      expect(groupIdentifierInput.element.value).toBe(group.groupIdentifier);
      expect(groupIdentifierInput.element.disabled).toBe(false);
    });
  });
});
