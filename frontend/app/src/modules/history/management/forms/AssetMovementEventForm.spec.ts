import type { AssetMap } from '@/types/asset';
import type { AssetMovementEvent } from '@/types/history/events';
import type { TradeLocationData } from '@/types/history/trade/location';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useHistoryEvents } from '@/composables/history/events';
import { useLocations } from '@/composables/locations';
import AssetMovementEventForm from '@/modules/history/management/forms/AssetMovementEventForm.vue';
import { useBalancePricesStore } from '@/store/balances/prices';
import { setupDayjs } from '@/utils/date';
import { bigNumberify, HistoryEventEntryType, One } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import flushPromises from 'flush-promises';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    getHistoricPrice: vi.fn(),
  }),
}));

vi.mock('@/composables/history/events', () => ({
  useHistoryEvents: vi.fn(),
}));

vi.mock('@/composables/locations', () => ({
  useLocations: vi.fn(),
}));

describe('forms/AssetMovementEventForm.vue', () => {
  let addHistoryEventMock: ReturnType<typeof vi.fn>;
  let editHistoryEventMock: ReturnType<typeof vi.fn>;
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

  const group: AssetMovementEvent = {
    amount: bigNumberify(10),
    asset: asset.symbol,
    entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
    eventIdentifier: 'STJ6KRHJYGA',
    eventSubtype: 'remove asset',
    eventType: 'withdrawal',
    extraData: null,
    identifier: 449,
    location: 'kraken',
    locationLabel: 'Kraken 1',
    notes: 'History event notes',
    sequenceIndex: 20,
    timestamp: 1696741486185,
  };

  beforeAll(() => {
    setupDayjs();
    vi.useFakeTimers();
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    addHistoryEventMock = vi.fn();
    editHistoryEventMock = vi.fn();

    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    vi.mocked(useBalancePricesStore().getHistoricPrice).mockResolvedValue(One);

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
  });

  afterEach(() => {
    wrapper.unmount();
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
    vi.advanceTimersToNextTimer();

    expect((wrapper.find('[data-cy=eventIdentifier] input').element as HTMLInputElement).value).toBe('');
    expect((wrapper.find('[data-cy=locationLabel] .input-value').element as HTMLInputElement).value).toBe('');
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

    vi.advanceTimersToNextTimer();

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
      notes: 'Test deposit transaction',
      timestamp: nowInMs,
      uniqueId: '1234567890',
    });
  });

  it('it should update the fields when all editing an event', async () => {
    wrapper = createWrapper();
    vi.advanceTimersToNextTimer();
    await wrapper.setProps({ data: { eventsInGroup: [group], nextSequenceId: '1', type: 'edit-group' } });
    vi.advanceTimersToNextTimer();

    expect((wrapper.find('[data-cy=eventIdentifier] input').element as HTMLInputElement).value).toBe(
      group.eventIdentifier,
    );

    expect((wrapper.find('[data-cy=locationLabel] .input-value').element as HTMLInputElement).value).toBe(
      group.locationLabel,
    );

    expect((wrapper.find('[data-cy=amount] input').element as HTMLInputElement).value).toBe(
      group.amount.toString(),
    );

    expect(
      (wrapper.find('[data-cy=notes] textarea:not([aria-hidden="true"])').element as HTMLTextAreaElement).value,
    ).toBe(group.notes);
  });

  it('should call editHistoryEvent when editing an event', async () => {
    wrapper = createWrapper({
      props: { data: { eventsInGroup: [group], nextSequenceId: '1', type: 'edit-group' } },
    });
    vi.advanceTimersToNextTimer();

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
        eventIdentifier: group.eventIdentifier,
        eventType: group.eventType,
        fee: null,
        feeAsset: null,
        identifier: group.identifier,
        location: group.location,
        locationLabel: group.locationLabel,
        notes: 'Test deposit transaction',
        timestamp: group.timestamp,
        uniqueId: '',
      }),
    );
  });

  it('should show eventTypes options correctly', async () => {
    wrapper = createWrapper({ props: { data: { eventsInGroup: [group], nextSequenceId: '1', type: 'edit-group' } } });
    vi.advanceTimersToNextTimer();
    await flushPromises();

    expect(wrapper.findAll('[data-cy=eventType] .selections span')).toHaveLength(2);
  });
});
