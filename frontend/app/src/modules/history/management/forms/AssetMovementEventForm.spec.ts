import type { AssetMap } from '@/types/asset';
import type { AssetMovementEvent } from '@/types/history/events/schemas';
import type { TradeLocationData } from '@/types/history/trade/location';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { useHistoryEvents } from '@/composables/history/events';
import { useLocations } from '@/composables/locations';
import AssetMovementEventForm from '@/modules/history/management/forms/AssetMovementEventForm.vue';
import { usePriceTaskManager } from '@/modules/prices/use-price-task-manager';
import { setupDayjs } from '@/utils/date';
import { bigNumberify, HistoryEventEntryType, One } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import flushPromises from 'flush-promises';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { nextTick } from 'vue';

vi.mock('@/modules/prices/use-price-task-manager', () => ({
  usePriceTaskManager: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

vi.mock('@/composables/history/events', () => ({
  useHistoryEvents: vi.fn(),
}));

vi.mock('@/composables/locations', () => ({
  useLocations: vi.fn(),
}));

vi.mock('@/composables/api/assets/prices', () => ({
  useAssetPricesApi: vi.fn().mockReturnValue({
    addHistoricalPrice: vi.fn(),
  }),
}));

describe('forms/AssetMovementEventForm.vue', () => {
  let addHistoryEventMock: ReturnType<typeof vi.fn>;
  let editHistoryEventMock: ReturnType<typeof vi.fn>;
  let addHistoricalPriceMock: ReturnType<typeof vi.fn>;
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
    eventIdentifier: 'STJ6KRHJYGA',
    eventSubtype: 'remove asset',
    eventType: 'withdrawal',
    extraData: {
      reference: 'TEST123',
    },
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
    eventIdentifier: 'STJ6KRHJYGA',
    eventSubtype: 'fee',
    eventType: 'withdrawal',
    extraData: {
      reference: 'TEST123',
    },
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
    addHistoryEventMock = vi.fn();
    editHistoryEventMock = vi.fn();
    addHistoricalPriceMock = vi.fn();

    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    vi.mocked(usePriceTaskManager().getHistoricPrice).mockResolvedValue(One);

    (useLocations as Mock).mockReturnValue({
      tradeLocations: computed<TradeLocationData[]>(() => [{
        identifier: 'kraken',
        name: 'Kraken',
      }]),
    });

    (useHistoryEvents as Mock).mockReturnValue({
      addHistoryEvent: addHistoryEventMock,
      editHistoryEvent: editHistoryEventMock,
    });

    (useAssetPricesApi as Mock).mockReturnValue({
      addHistoricalPrice: addHistoricalPriceMock,
    });
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

  it('should show the default state when adding a new event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find<HTMLInputElement>('[data-cy=eventIdentifier] input').element.value).toBe('');
    expect(wrapper.find<HTMLInputElement>('[data-cy=locationLabel] .input-value').element.value).toBe('');
  });

  it.each([{
    fee: null,
    feeAsset: null,
  }, {
    fee: '0.00001',
    feeAsset: 'BTC',
  }])('should call addHistoryEvent when adding a new event with fee $feeAsset', async ({ fee, feeAsset }) => {
    wrapper = createWrapper();

    const now = dayjs();
    const nowInMs = now.valueOf();
    await wrapper.find('[data-cy=datetime] input').setValue(dayjs(nowInMs).format('DD/MM/YYYY HH:mm:ss.SSS'));
    await wrapper.find('[data-cy=eventIdentifier] input').setValue('TEST123');
    await wrapper.find('[data-cy=eventType] input').setValue('deposit');
    await wrapper.find('[data-cy=locationLabel] input').setValue('Kraken 1');
    await wrapper.find('[data-cy=location] input').setValue('kraken');
    await wrapper.find('[data-cy=asset] input').setValue('BTC');
    await wrapper.find('[data-cy=amount] input').setValue('2.5');
    await wrapper.find('[data-cy=notes] textarea:not([aria-hidden="true"])').setValue('Test deposit transaction');
    await wrapper.find('[data-cy=unique-id] input').setValue('1234567890');

    if (fee && feeAsset) {
      await wrapper.find('[data-cy=has-fee] input').setValue(true);
      await wrapper.find('[data-cy=fee-amount] input').setValue(fee.toString());
      await wrapper.find('[data-cy=fee-asset] input').setValue(feeAsset.toString());
    }

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(addHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify('2.5'),
      asset: 'BTC',
      entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
      eventIdentifier: 'TEST123',
      eventType: 'deposit',
      fee,
      feeAsset,
      location: 'kraken',
      locationLabel: 'Kraken 1',
      timestamp: nowInMs,
      uniqueId: '1234567890',
      userNotes: fee ? ['Test deposit transaction', ''] : ['Test deposit transaction'],
    });
  });

  it('should display validation errors when the form is invalid', async () => {
    wrapper = createWrapper();
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-cy=amount] .details').exists()).toBe(true);
    expect(wrapper.find('[data-cy=asset] .details').exists()).toBe(true);
  });

  it('it should update the fields when all editing an event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { eventsInGroup: [event], type: 'edit-group' } });
    await vi.advanceTimersToNextTimerAsync();

    const eventIdentifierInput = wrapper.find<HTMLInputElement>('[data-cy=eventIdentifier] input');
    const locationLabelInput = wrapper.find<HTMLInputElement>('[data-cy=locationLabel] .input-value');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const notesTextArea = wrapper.find<HTMLTextAreaElement>('[data-cy=notes] textarea:not([aria-hidden="true"])');

    expect(eventIdentifierInput.element.value).toBe(event.eventIdentifier);
    expect(locationLabelInput.element.value).toBe(event.locationLabel);
    expect(amountInput.element.value).toBe(event.amount.toString());
    expect(notesTextArea.element.value).toBe(event.userNotes);
  });

  it('should not call editHistoryEvent when only updating the historic price', async () => {
    wrapper = createWrapper({
      props: { data: { eventsInGroup: [event], type: 'edit-group' } },
    });
    await vi.advanceTimersToNextTimerAsync();
    const saveMethod = wrapper.vm.save;

    // click save without changing anything
    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoricalPriceMock.mockResolvedValueOnce({ success: true });

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

  it('should call editHistoryEvent when editing an event', async () => {
    wrapper = createWrapper({
      props: { data: { eventsInGroup: [event], type: 'edit-group' } },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-cy=asset] input').setValue('USD');
    await wrapper.find('[data-cy=amount] input').setValue('250');
    await wrapper.find('[data-cy=notes] textarea:not([aria-hidden="true"])').setValue('Test deposit transaction');

    const saveMethod = wrapper.vm.save;
    editHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(editHistoryEventMock).toHaveBeenCalledWith(
      expect.objectContaining({
        amount: bigNumberify('250'),
        asset: 'USD',
        entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
        eventIdentifier: event.eventIdentifier,
        eventType: event.eventType,
        fee: null,
        feeAsset: null,
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

    await wrapper.find('[data-cy=has-fee] input').setValue(true);
    await wrapper.find('[data-cy=fee-amount] input').setValue(fee.amount.toString());
    await wrapper.find('[data-cy=fee-asset] input').setValue(fee.asset.toString());

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(editHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify('10'),
      asset: 'ETH',
      entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
      eventIdentifier: event.eventIdentifier,
      eventType: event.eventType,
      fee: fee.amount.toString(),
      feeAsset: fee.asset,
      identifier: event.identifier,
      location: event.location,
      locationLabel: event.locationLabel,
      timestamp: event.timestamp,
      uniqueId: 'TEST123',
      userNotes: ['History event notes', ''],
    });
  });

  it('should remove the fee when the users checks out the fee checkbox', async () => {
    wrapper = createWrapper({
      props: { data: { eventsInGroup: [event, fee], type: 'edit-group' } },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-cy=has-fee] input').setValue(false);
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
        eventIdentifier: event.eventIdentifier,
        eventType: event.eventType,
        fee: null,
        feeAsset: null,
        identifier: event.identifier,
        location: event.location,
        locationLabel: event.locationLabel,
        timestamp: event.timestamp,
        uniqueId: 'TEST123',
        userNotes: ['History event notes'],
      }),
    );
  });

  it('should show eventTypes options correctly', async () => {
    wrapper = createWrapper({ props: { data: { eventsInGroup: [event], type: 'edit-group' } } });
    await vi.advanceTimersToNextTimerAsync();
    await flushPromises();

    expect(wrapper.findAll('[data-cy=eventType] .selections span')).toHaveLength(2);
  });
});
