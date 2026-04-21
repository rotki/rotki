import type { AssetMap } from '@/modules/assets/types';
import type { TradeLocationData } from '@/modules/core/common/location';
import type { EvmHistoryEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
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
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';
import EvmEventForm from '@/modules/history/management/forms/EvmEventForm.vue';

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
  useAssetPricesApi: vi.fn().mockReturnValue({
    addHistoricalPrice: vi.fn(),
  }),
}));

describe('forms/EvmEventForm.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof EvmEventForm>>;
  let addHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>>;
  let editHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>>;
  let addHistoricalPriceMock: ReturnType<typeof vi.fn<ReturnType<typeof useAssetPricesApi>['addHistoricalPrice']>>;
  let pinia: Pinia;

  const asset = {
    assetType: 'own chain',
    isCustomAsset: false,
    name: 'Ethereum',
    symbol: 'eip155:1/erc20:0xA3Ee8CEB67906492287FFD256A9422313B5796d4',
  };

  const mapping: AssetMap = {
    assetCollections: {},
    assets: { [asset.symbol]: asset },
  };

  const group: EvmHistoryEvent = {
    address: '0x30a2EBF10f34c6C4874b0bDD5740690fD2f3B70C',
    amount: bigNumberify(610),
    asset: asset.symbol,
    counterparty: null,
    entryType: HistoryEventEntryType.EVM_EVENT,
    eventSubtype: '',
    eventType: 'receive',
    groupIdentifier: '10x4ba949779d936631dc9eb68fa9308c18de51db253aeea919384c728942f95ba9',
    identifier: 14344,
    location: 'ethereum',
    locationLabel: '0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8',
    sequenceIndex: 2411,
    timestamp: 1686495083,
    txRef: '0x4ba949779d936631dc9eb68fa9308c18de51db253aeea919384c728942f95ba9',
    userNotes:
      'Receive 610 Visit https://rafts.cc to claim rewards. from 0x30a2EBF10f34c6C4874b0bDD5740690fD2f3B70C to 0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8',
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
    vi.mocked(useLocations).mockReturnValue({
      getExchangeName: vi.fn<ReturnType<typeof useLocations>['getExchangeName']>(),
      getLocationData: vi.fn<ReturnType<typeof useLocations>['getLocationData']>(),
      useLocationData: vi.fn<ReturnType<typeof useLocations>['useLocationData']>(),
      tradeLocations: computed<TradeLocationData[]>(() => [{
        identifier: 'ethereum',
        name: 'Ethereum',
      }]),
    });
    vi.mocked(useHistoryEvents).mockReturnValue({
      addHistoryEvent: addHistoryEventMock,
      deleteHistoryEvent: vi.fn<ReturnType<typeof useHistoryEvents>['deleteHistoryEvent']>(),
      editHistoryEvent: editHistoryEventMock,
      fetchHistoryEvents: vi.fn<ReturnType<typeof useHistoryEvents>['fetchHistoryEvents']>(),
      getEarliestEventTimestamp: vi.fn<ReturnType<typeof useHistoryEvents>['getEarliestEventTimestamp']>(),
    });
    vi.mocked(useAssetPricesApi).mockReturnValue({
      addHistoricalPrice: addHistoricalPriceMock,
      addLatestPrice: vi.fn<ReturnType<typeof useAssetPricesApi>['addLatestPrice']>(),
      deleteHistoricalPrice: vi.fn<ReturnType<typeof useAssetPricesApi>['deleteHistoricalPrice']>(),
      deleteLatestPrice: vi.fn<ReturnType<typeof useAssetPricesApi>['deleteLatestPrice']>(),
      editHistoricalPrice: vi.fn<ReturnType<typeof useAssetPricesApi>['editHistoricalPrice']>(),
      fetchHistoricalPrices: vi.fn<ReturnType<typeof useAssetPricesApi>['fetchHistoricalPrices']>(),
      fetchLatestPrices: vi.fn<ReturnType<typeof useAssetPricesApi>['fetchLatestPrices']>(),
      fetchNftsPrices: vi.fn<ReturnType<typeof useAssetPricesApi>['fetchNftsPrices']>(),
      fetchOraclePrices: vi.fn<ReturnType<typeof useAssetPricesApi>['fetchOraclePrices']>(),
    });
  });

  afterEach(() => {
    wrapper.unmount();
    vi.useRealTimers();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof EvmEventForm> = {
    props: {
      data: { nextSequenceId: '0', type: 'add' },
    },
  }): VueWrapper<InstanceType<typeof EvmEventForm>> =>
    mount(EvmEventForm, {
      global: {
        plugins: [pinia],
        stubs: {
          I18nT: true,
        },
      },
      ...options,
    });

  it('should show the default state when opening the form without any data', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const txRefInput = wrapper.find<HTMLInputElement>('[data-cy=tx-ref] input');
    const locationInput = wrapper.find<HTMLInputElement>('[data-cy=location-label] input');
    const addressInput = wrapper.find<HTMLInputElement>('[data-cy=address] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');

    expect(txRefInput.element.value).toBe('');
    expect(locationInput.element.value).toBe('');
    expect(addressInput.element.value).toBe('');
    expect(sequenceIndexInput.element.value).toBe('0');
  });

  it('should update the proper fields adding an event to a group', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { group, nextSequenceId: '10', type: 'group-add' } });

    const txRefInput = wrapper.find<HTMLInputElement>('[data-cy=tx-ref] input');
    const locationLabelInput = wrapper.find<HTMLInputElement>('[data-cy=location-label] input');
    const addressInput = wrapper.find<HTMLInputElement>('[data-cy=address] input');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');
    const noteTextArea = wrapper.find<HTMLTextAreaElement>('[data-cy=notes] textarea:not([aria-hidden="true"])');

    expect(txRefInput.element.value).toBe(group.txRef);
    expect(locationLabelInput.element.value).toBe(group.locationLabel);
    expect(addressInput.element.value).toBe(group.address);
    expect(amountInput.element.value).toBe('0');
    expect(sequenceIndexInput.element.value).toBe('10');
    expect(noteTextArea.element.value).toBe('');
  });

  it('should update the fields when editing an event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { event: group, nextSequenceId: '10', type: 'edit' } });

    const txRefInput = wrapper.find<HTMLInputElement>('[data-cy=tx-ref] input');
    const locationLabelInput = wrapper.find<HTMLInputElement>('[data-cy=location-label] input');
    const addressInput = wrapper.find<HTMLInputElement>('[data-cy=address] input');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');
    const notesTextArea = wrapper.find<HTMLTextAreaElement>('[data-cy=notes] textarea:not([aria-hidden="true"])');

    expect(txRefInput.element.value).toBe(group.txRef);
    expect(locationLabelInput.element.value).toBe(group.locationLabel);
    expect(addressInput.element.value).toBe(group.address);
    expect(amountInput.element.value).toBe(group.amount.toString());
    expect(sequenceIndexInput.element.value.replace(',', '')).toBe(group.sequenceIndex.toString());
    expect(notesTextArea.element.value).toBe(group.userNotes);
  });

  it('should show all eventTypes options correctly', async () => {
    wrapper = createWrapper({ props: { data: { group, nextSequenceId: '1', type: 'group-add' } } });
    await vi.advanceTimersToNextTimerAsync();

    const { historyEventTypesData } = useHistoryEventMappings();

    expect(wrapper.findAll('[data-cy=eventType] .selections span')).toHaveLength(get(historyEventTypesData).length);
  });

  it('should show all eventSubTypes options correctly', async () => {
    wrapper = createWrapper({ props: { data: { group, nextSequenceId: '1', type: 'group-add' } } });
    await vi.advanceTimersToNextTimerAsync();

    const { historyEventSubTypesData } = useHistoryEventMappings();

    expect(wrapper.findAll('[data-cy=eventSubtype] .selections span')).toHaveLength(
      get(historyEventSubTypesData).length,
    );
  });

  it('should show all counterparties options correctly', async () => {
    wrapper = createWrapper({ props: { data: { group, nextSequenceId: '1', type: 'group-add' } } });
    await vi.advanceTimersToNextTimerAsync();

    const { counterparties } = useHistoryEventCounterpartyMappings();

    expect(wrapper.findAll('[data-cy=counterparty] .selections span')).toHaveLength(get(counterparties).length);
  });

  it('should show correct eventSubtypes options, based on selected eventType and counterparty', async () => {
    wrapper = createWrapper({ props: { data: { group, nextSequenceId: '1', type: 'group-add' } } });
    await vi.advanceTimersToNextTimerAsync();

    const { historyEventTypeGlobalMapping } = useHistoryEventMappings();

    const selectedEventType = 'deposit';

    await wrapper.find('[data-cy=eventType] .input-value').trigger('input', {
      value: selectedEventType,
    });

    await vi.advanceTimersToNextTimerAsync();

    const keysFromGlobalMappings = Object.keys(get(historyEventTypeGlobalMapping)?.[selectedEventType] ?? {});

    const spans = wrapper.findAll('[data-cy=eventSubtype] .selections span');
    expect(spans).toHaveLength(keysFromGlobalMappings.length);

    for (let i = 0; i < keysFromGlobalMappings.length; i++)
      expect(keysFromGlobalMappings).toContain(spans.at(i)!.text());
  });

  it('should add a new evm event when form is submitted', async () => {
    wrapper = createWrapper();
    await nextTick();
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-cy=tx-ref] input').setValue(group.txRef);
    await wrapper.find('[data-cy=location] input').setValue(group.location);
    await wrapper.find('[data-cy=location-label] input').setValue(group.locationLabel);
    await wrapper.find('[data-cy=eventType] input').setValue(group.eventType);
    await wrapper.find('[data-cy=asset] input').setValue(group.asset);
    await wrapper.find('[data-cy=amount] input').setValue('610'); // Using the numeric value from group.amount
    await wrapper.find('[data-cy=address] input').setValue(group.address);
    await wrapper.find('[data-cy=sequence-index] input').setValue(group.sequenceIndex);
    await wrapper.find('[data-cy=notes] textarea:not([aria-hidden="true"])').setValue(group.userNotes);
    await wrapper.find('[data-cy=datetime] input').setValue(dayjs(group.timestamp).format('DD/MM/YYYY HH:mm:ss.SSS'));

    // group.counterparty is null, so no counterparty field to set
    // group.eventSubtype is '', so no eventSubtype field to set

    const saveMethod = wrapper.vm.save;

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(addHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(addHistoryEventMock).toHaveBeenCalledWith({
      address: group.address,
      amount: group.amount,
      asset: group.asset,
      counterparty: group.counterparty,
      entryType: HistoryEventEntryType.EVM_EVENT,
      eventSubtype: 'none',
      eventType: group.eventType,
      extraData: {},
      groupIdentifier: null,
      location: group.location,
      locationLabel: group.locationLabel,
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
    await wrapper.find('[data-cy=primary] input').setValue('1000');

    await saveMethod();
    await nextTick();
    expect(editHistoryEventMock).not.toHaveBeenCalled();
  });

  it('should edit an existing evm event when form is submitted', async () => {
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

    await wrapper.find('[data-cy=amount] input').setValue('650'); // Using the numeric value from group.amount
    await wrapper.find('[data-cy=sequence-index] input').setValue('2111');
    await wrapper.find('[data-cy=notes] textarea:not([aria-hidden="true"])').setValue('user note');

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(editHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(editHistoryEventMock).toHaveBeenCalledWith({
      address: group.address,
      amount: bigNumberify('650'),
      asset: group.asset,
      counterparty: group.counterparty,
      entryType: HistoryEventEntryType.EVM_EVENT,
      eventSubtype: 'none',
      eventType: group.eventType,
      extraData: {},
      groupIdentifier: group.groupIdentifier,
      identifier: group.identifier,
      location: group.location,
      locationLabel: group.locationLabel,
      sequenceIndex: '2111',
      timestamp: group.timestamp,
      txRef: group.txRef,
      userNotes: 'user note',
    });
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

    editHistoryEventMock.mockResolvedValueOnce({
      message: { location: ['invalid location'] },
      success: false,
    });

    await wrapper.find('[data-cy=amount] input').setValue('4.5');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    const saveResult = await saveMethod();
    await nextTick();

    expect(editHistoryEventMock).toHaveBeenCalled();
    expect(saveResult).toBe(false);
    expect(wrapper.find('[data-cy=location] .details').text()).toBe('invalid location');
  });

  it('should display validation errors when the form is invalid', async () => {
    wrapper = createWrapper();
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-cy=amount] .details').exists()).toBe(true);
    expect(wrapper.find('[data-cy=asset] .details').exists()).toBe(true);
  });

  describe('actualGroupIdentifier', () => {
    const eventWithActualGroupIdentifier: EvmHistoryEvent = {
      ...group,
      actualGroupIdentifier: 'ACTUAL123',
      groupIdentifier: 'LINKED456',
    };

    it('should use actualGroupIdentifier when present and disable the field', async () => {
      wrapper = createWrapper({
        props: { data: { event: eventWithActualGroupIdentifier, nextSequenceId: '10', type: 'edit' } },
      });
      await vi.advanceTimersToNextTimerAsync();

      const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-cy=groupIdentifier] input');
      expect(groupIdentifierInput.element.value).toBe('ACTUAL123');
      expect(groupIdentifierInput.element.disabled).toBe(true);
    });

    it('should use groupIdentifier when actualGroupIdentifier is not present', async () => {
      wrapper = createWrapper({
        props: { data: { event: group, nextSequenceId: '10', type: 'edit' } },
      });
      await vi.advanceTimersToNextTimerAsync();

      const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-cy=groupIdentifier] input');
      expect(groupIdentifierInput.element.value).toBe(group.groupIdentifier);
      expect(groupIdentifierInput.element.disabled).toBe(false);
    });
  });
});
