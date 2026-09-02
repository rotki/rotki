import type { AssetMap } from '@/modules/assets/types';
import type { TradeLocationData } from '@/modules/core/common/location';
import type { AssetMovementEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType, One } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { selectorContract } from '@test/utils/selector-contract';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import flushPromises from 'flush-promises';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { setupDayjs } from '@/modules/core/common/data/date';
import { useLocations } from '@/modules/core/common/use-locations';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';
import AssetMovementEventForm from '@/modules/history/management/forms/AssetMovementEventForm.vue';

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
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

describe('forms/AssetMovementEventForm.vue', () => {
  let addHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>>;
  let editHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>>;
  let addHistoricalPriceMock: ReturnType<typeof vi.fn<ReturnType<typeof useAssetPricesApi>['addHistoricalPrice']>>;
  let wrapper: VueWrapper<InstanceType<typeof AssetMovementEventForm>>;
  let pinia: Pinia;

  const asset = {
    assetType: 'own chain',
    isCustomAsset: false,
    name: 'Ethereum',
    symbol: 'ETH',
  };

  const mapping: AssetMap = {
    assetCollections: {},
    assets: { [asset.symbol]: asset },
  };

  const event: AssetMovementEvent = {
    amount: bigNumberify(10),
    asset: asset.symbol,
    entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
    eventSubtype: 'spend',
    eventType: 'withdrawal',
    extraData: {
      blockchain: 'optimism',
      reference: 'TEST123',
      transactionId: '0x9834594deca004e626ea06c287abab60003f3752402a2b09ca88657db50292cf',
    },
    groupIdentifier: 'STJ6KRHJYGA',
    identifier: 449,
    location: 'kraken',
    locationLabel: 'Kraken 1',
    sequenceIndex: 0,
    timestamp: 1696741486185,
    userNotes: 'History event notes',
  };

  const fee: AssetMovementEvent = {
    amount: bigNumberify(0.1),
    asset: asset.symbol,
    entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
    eventSubtype: 'fee',
    eventType: 'withdrawal',
    extraData: {
      reference: 'TEST123',
    },
    groupIdentifier: 'STJ6KRHJYGA',
    identifier: 450,
    location: 'kraken',
    locationLabel: 'Kraken 1',
    sequenceIndex: 1,
    timestamp: 1696741486185,
    userNotes: 'History event notes',
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
    vi.mocked(usePriceTaskManager().getHistoricPrice).mockResolvedValue(One);

    vi.mocked(useLocations).mockReturnValue(createMock<ReturnType<typeof useLocations>>({
      tradeLocations: computed<TradeLocationData[]>(() => [{
        identifier: 'kraken',
        name: 'Kraken',
      }]),
    }));

    vi.mocked(useHistoryEvents).mockReturnValue(createMock<ReturnType<typeof useHistoryEvents>>({
      addHistoryEvent: addHistoryEventMock,
      editHistoryEvent: editHistoryEventMock,
    }));

    vi.mocked(useAssetPricesApi).mockReturnValue(createMock<ReturnType<typeof useAssetPricesApi>>({
      addHistoricalPrice: addHistoricalPriceMock,
    }));
  });

  afterEach(() => {
    wrapper.unmount();
    vi.useRealTimers();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof AssetMovementEventForm> = {
    props: {
      data: { nextSequenceId: '0', type: 'add' },
    },
  }): VueWrapper<InstanceType<typeof AssetMovementEventForm>> => mount(AssetMovementEventForm, {
    global: {
      plugins: [pinia],
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
        "data-testid=asset-movement-event-form-advance",
        "data-testid=blockchain-id",
        "data-testid=datetime",
        "data-testid=event-subtype",
        "data-testid=fee-amount",
        "data-testid=fee-asset",
        "data-testid=group-identifier",
        "data-testid=grouped-amount-input-swap",
        "data-testid=has-fee",
        "data-testid=location",
        "data-testid=location-label",
        "data-testid=notes",
        "data-testid=primary",
        "data-testid=secondary",
        "data-testid=tx-ref",
        "data-testid=unique-id",
      ]
    `);
  });

  it('should show the default state when adding a new event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input').element.value).toBe('');
    expect(wrapper.find<HTMLInputElement>('[data-testid=location-label] .input-value').element.value).toBe('');
  });

  it('should call addHistoryEvent when adding a new event without fee', async () => {
    wrapper = createWrapper();

    const now = dayjs();
    const nowInMs = now.valueOf();
    await wrapper.find('[data-testid=datetime] input').setValue(dayjs(nowInMs).format('DD/MM/YYYY HH:mm:ss.SSS'));
    await wrapper.find('[data-testid=group-identifier] input').setValue('TEST123');
    await wrapper.find('[data-testid=event-subtype] input').setValue('receive');
    await wrapper.find('[data-testid=location-label] input').setValue('Kraken 1');
    await wrapper.find('[data-testid=location] input').setValue('kraken');
    await wrapper.find('[data-testid=asset] input').setValue('BTC');
    await wrapper.find('[data-testid=amount] input').setValue('2.5');
    await wrapper.find('[data-testid=notes] textarea:not([aria-hidden="true"])').setValue('Test deposit transaction');
    await wrapper.find('[data-testid=unique-id] input').setValue('1234567890');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(addHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify('2.5'),
      asset: 'BTC',
      blockchain: '',
      entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
      eventSubtype: 'receive',
      fee: null,
      feeAsset: null,
      groupIdentifier: 'TEST123',
      location: 'kraken',
      locationLabel: 'Kraken 1',
      timestamp: nowInMs,
      transactionId: '',
      uniqueId: '1234567890',
      userNotes: ['Test deposit transaction'],
    });
  });

  it('should call addHistoryEvent when adding a new event with fee BTC', async () => {
    wrapper = createWrapper();

    const now = dayjs();
    const nowInMs = now.valueOf();
    await wrapper.find('[data-testid=datetime] input').setValue(dayjs(nowInMs).format('DD/MM/YYYY HH:mm:ss.SSS'));
    await wrapper.find('[data-testid=group-identifier] input').setValue('TEST123');
    await wrapper.find('[data-testid=event-subtype] input').setValue('receive');
    await wrapper.find('[data-testid=location-label] input').setValue('Kraken 1');
    await wrapper.find('[data-testid=location] input').setValue('kraken');
    await wrapper.find('[data-testid=asset] input').setValue('BTC');
    await wrapper.find('[data-testid=amount] input').setValue('2.5');
    await wrapper.find('[data-testid=notes] textarea:not([aria-hidden="true"])').setValue('Test deposit transaction');
    await wrapper.find('[data-testid=unique-id] input').setValue('1234567890');

    await wrapper.find('[data-testid=has-fee] input').setValue(true);
    await wrapper.find('[data-testid=fee-amount] input').setValue('0.00001');
    await wrapper.find('[data-testid=fee-asset] input').setValue('BTC');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(addHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify('2.5'),
      asset: 'BTC',
      blockchain: '',
      entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
      eventSubtype: 'receive',
      fee: '0.00001',
      feeAsset: 'BTC',
      groupIdentifier: 'TEST123',
      location: 'kraken',
      locationLabel: 'Kraken 1',
      timestamp: nowInMs,
      transactionId: '',
      uniqueId: '1234567890',
      userNotes: ['Test deposit transaction', ''],
    });
  });

  it('should display validation errors when the form is invalid', async () => {
    wrapper = createWrapper();
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-testid=amount] .details').exists()).toBe(true);
    expect(wrapper.find('[data-testid=asset] .details').exists()).toBe(true);
  });

  it('should update the fields when all editing an event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { eventsInGroup: [event], type: 'edit-group' } });
    await vi.advanceTimersToNextTimerAsync();

    const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
    const locationLabelInput = wrapper.find<HTMLInputElement>('[data-testid=location-label] .input-value');
    const amountInput = wrapper.find<HTMLInputElement>('[data-testid=amount] input');
    const notesTextArea = wrapper.find<HTMLTextAreaElement>('[data-testid=notes] textarea:not([aria-hidden="true"])');

    expect(groupIdentifierInput.element.value).toBe(event.groupIdentifier);
    expect(locationLabelInput.element.value).toBe(event.locationLabel);
    expect(amountInput.element.value).toBe(event.amount.toString());
    expect(notesTextArea.element.value).toBe(event.userNotes);
  });

  it('should not call editHistoryEvent when nothing changed', async () => {
    wrapper = createWrapper({
      props: { data: { eventsInGroup: [event], type: 'edit-group' } },
    });
    await vi.advanceTimersToNextTimerAsync();

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoricalPriceMock.mockResolvedValueOnce(true);

    await wrapper.vm.save();
    await nextTick();
    expect(editHistoryEventMock).not.toHaveBeenCalled();
  });

  it('should not call editHistoryEvent when the historic price is the only edit', async () => {
    wrapper = createWrapper({
      props: { data: { eventsInGroup: [event], type: 'edit-group' } },
    });
    await vi.advanceTimersToNextTimerAsync();

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoricalPriceMock.mockResolvedValueOnce(true);
    await wrapper.find('[data-testid=primary] input').setValue('1000');

    await wrapper.vm.save();
    await nextTick();
    expect(editHistoryEventMock).not.toHaveBeenCalled();
  });

  it('should not save the event when the historic price fails to write', async () => {
    wrapper = createWrapper({
      props: { data: { eventsInGroup: [event], type: 'edit-group' } },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-testid=primary] input').setValue('1000');
    await wrapper.find('[data-testid=amount] input').setValue('250');

    addHistoricalPriceMock.mockRejectedValueOnce(new Error('price rejected'));

    const saved = await wrapper.vm.save();
    await nextTick();

    expect(addHistoricalPriceMock).toHaveBeenCalled();
    expect(editHistoryEventMock).not.toHaveBeenCalled();
    expect(saved).toBe(false);
  });

  it('should call editHistoryEvent when editing an event', async () => {
    wrapper = createWrapper({
      props: { data: { eventsInGroup: [event], type: 'edit-group' } },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-testid=asset] input').setValue('USD');
    await wrapper.find('[data-testid=amount] input').setValue('250');
    await wrapper.find('[data-testid=notes] textarea:not([aria-hidden="true"])').setValue('Test deposit transaction');

    const saveMethod = wrapper.vm.save;
    editHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(editHistoryEventMock).toHaveBeenCalledWith(
      expect.objectContaining({
        amount: bigNumberify('250'),
        asset: 'USD',
        entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
        eventSubtype: 'spend',
        fee: null,
        feeAsset: null,
        groupIdentifier: event.groupIdentifier,
        identifier: event.identifier,
        location: event.location,
        locationLabel: event.locationLabel,
        timestamp: event.timestamp,
        uniqueId: 'TEST123',
        userNotes: ['Test deposit transaction'],
      }),
    );
  });

  it('should add the fee when the users checks out the fee checkbox', async () => {
    wrapper = createWrapper({
      props: { data: { eventsInGroup: [event], type: 'edit-group' } },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-testid=has-fee] input').setValue(true);
    await wrapper.find('[data-testid=fee-amount] input').setValue(fee.amount.toString());
    await wrapper.find('[data-testid=fee-asset] input').setValue(fee.asset.toString());

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(editHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify('10'),
      asset: 'ETH',
      blockchain: event.extraData?.blockchain,
      entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
      eventSubtype: 'spend',
      fee: fee.amount.toString(),
      feeAsset: fee.asset,
      groupIdentifier: event.groupIdentifier,
      identifier: event.identifier,
      location: event.location,
      locationLabel: event.locationLabel,
      timestamp: event.timestamp,
      transactionId: event.extraData?.transactionId,
      uniqueId: event.extraData?.reference,
      userNotes: ['History event notes', ''],
    });
  });

  it('should remove the fee when the users checks out the fee checkbox', async () => {
    wrapper = createWrapper({
      props: { data: { eventsInGroup: [event, fee], type: 'edit-group' } },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-testid=has-fee] input').setValue(false);
    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(editHistoryEventMock).toHaveBeenCalledWith(
      expect.objectContaining({
        amount: bigNumberify('10'),
        asset: 'ETH',
        entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
        eventSubtype: 'spend',
        fee: null,
        feeAsset: null,
        groupIdentifier: event.groupIdentifier,
        identifier: event.identifier,
        location: event.location,
        locationLabel: event.locationLabel,
        timestamp: event.timestamp,
        uniqueId: 'TEST123',
        userNotes: ['History event notes'],
      }),
    );
  });

  it('should auto-generate uniqueId when not provided on new event', async () => {
    const mockUUID = '550e8400-e29b-41d4-a716-446655440000';
    vi.spyOn(crypto, 'randomUUID').mockReturnValue(mockUUID);

    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const now = dayjs();
    const nowInMs = now.valueOf();
    await wrapper.find('[data-testid=datetime] input').setValue(dayjs(nowInMs).format('DD/MM/YYYY HH:mm:ss.SSS'));
    await wrapper.find('[data-testid=event-subtype] input').setValue('receive');
    await wrapper.find('[data-testid=location] input').setValue('kraken');
    await wrapper.find('[data-testid=asset] input').setValue('BTC');
    await wrapper.find('[data-testid=amount] input').setValue('2.5');

    await vi.advanceTimersToNextTimerAsync();

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await wrapper.vm.save();
    expect(saveResult).toBe(true);
    expect(addHistoryEventMock).toHaveBeenCalledWith(
      expect.objectContaining({
        uniqueId: mockUUID,
      }),
    );
  });

  it('should keep a blank unique id when editing rather than assigning one on every save', async () => {
    const withoutReference: AssetMovementEvent = { ...event, extraData: null };
    wrapper = createWrapper({
      props: { data: { eventsInGroup: [withoutReference], type: 'edit-group' } },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-testid=amount] input').setValue('250');
    editHistoryEventMock.mockResolvedValueOnce({ success: true });

    expect(await wrapper.vm.save()).toBe(true);
    expect(editHistoryEventMock).toHaveBeenCalledWith(expect.objectContaining({ uniqueId: '' }));
  });

  it('should show eventTypes options correctly', async () => {
    wrapper = createWrapper({ props: { data: { eventsInGroup: [event], type: 'edit-group' } } });
    await vi.advanceTimersToNextTimerAsync();
    await flushPromises();

    expect(wrapper.findAll('[data-testid=event-subtype] .selections span')).toHaveLength(2);
  });

  describe('actualGroupIdentifier', () => {
    const eventWithActualGroupIdentifier: AssetMovementEvent = {
      ...event,
      actualGroupIdentifier: 'ACTUAL123',
      groupIdentifier: 'LINKED456',
    };

    it('should use actualGroupIdentifier when present and disable the field', async () => {
      wrapper = createWrapper({
        props: { data: { eventsInGroup: [eventWithActualGroupIdentifier], type: 'edit-group' } },
      });
      await vi.advanceTimersToNextTimerAsync();

      const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
      expect(groupIdentifierInput.element.value).toBe('ACTUAL123');
      expect(groupIdentifierInput.element.disabled).toBe(true);
    });

    it('should use groupIdentifier when actualGroupIdentifier is not present', async () => {
      wrapper = createWrapper({
        props: { data: { eventsInGroup: [event], type: 'edit-group' } },
      });
      await vi.advanceTimersToNextTimerAsync();

      const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
      expect(groupIdentifierInput.element.value).toBe(event.groupIdentifier);
      expect(groupIdentifierInput.element.disabled).toBe(false);
    });
  });
});
