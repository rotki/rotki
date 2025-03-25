import type { AddSwapEventPayload, EventData, SwapEvent } from '@/types/history/events';
import type { TradeLocationData } from '@/types/history/trade/location';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useHistoryEvents } from '@/composables/history/events';
import { useLocations } from '@/composables/locations';
import SwapEventForm from '@/modules/history/management/forms/SwapEventForm.vue';
import { useMessageStore } from '@/store/message';
import { setupDayjs } from '@/utils/date';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { mount } from '@vue/test-utils';
import dayjs from 'dayjs';
import { afterEach, beforeAll, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { nextTick } from 'vue';

vi.mock('@/composables/history/events', () => ({
  useHistoryEvents: vi.fn(),
}));

vi.mock('@/store/message', () => ({
  useMessageStore: vi.fn(),
}));

vi.mock('@/composables/locations', () => ({
  useLocations: vi.fn(),
}));

vi.mock('@/composables/api/assets/info', () => ({
  useAssetInfoApi: vi.fn(),
}));

describe('forms/SwapEventForm', () => {
  let addHistoryEventMock: ReturnType<typeof vi.fn>;
  let editHistoryEventMock: ReturnType<typeof vi.fn>;
  let setMessageMock: ReturnType<typeof vi.fn>;

  const data: EventData<SwapEvent> = {
    eventsInGroup: [{
      amount: bigNumberify('0.01'),
      asset: 'ETH',
      description: 'Swap 0.01 ETH in Binance',
      entryType: 'swap event',
      eventIdentifier: '24bf5c3b2031b1224d7f0e642fde058ac8316039969762b67981372229fe1a7f',
      eventSubtype: 'spend',
      eventType: 'trade',
      extraData: null,
      identifier: 2737,
      location: 'binance',
      locationLabel: null,
      notes: 'note',
      sequenceIndex: 0,
      timestamp: 1742901211000,
    }, {
      amount: bigNumberify('20'),
      asset: 'USD',
      description: 'Receive 20 USD after a swap in Binance',
      entryType: 'swap event',
      eventIdentifier: '24bf5c3b2031b1224d7f0e642fde058ac8316039969762b67981372229fe1a7f',
      eventSubtype: 'receive',
      eventType: 'trade',
      extraData: null,
      identifier: 2738,
      location: 'binance',
      locationLabel: null,
      notes: '',
      sequenceIndex: 1,
      timestamp: 1742901211000,
    }, {
      amount: bigNumberify('1'),
      asset: 'USD',
      description: 'Spend 1 USD as Binance swap fee',
      entryType: 'swap event',
      eventIdentifier: '24bf5c3b2031b1224d7f0e642fde058ac8316039969762b67981372229fe1a7f',
      eventSubtype: 'fee',
      eventType: 'trade',
      extraData: null,
      identifier: 2739,
      location: 'binance',
      locationLabel: null,
      notes: '',
      sequenceIndex: 2,
      timestamp: 1742901211000,
    }],
  };

  beforeAll(() => {
    setupDayjs();
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    vi.useFakeTimers();
    addHistoryEventMock = vi.fn();
    editHistoryEventMock = vi.fn();
    setMessageMock = vi.fn();

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

    (useMessageStore as unknown as Mock).mockReturnValue({
      setMessage: setMessageMock,
    });

    (useAssetInfoApi as Mock).mockReturnValue({
      assetSearch: vi.fn(),
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should render the form correctly', () => {
    const wrapper = mount(SwapEventForm);
    expect(wrapper.exists()).toBe(true);
    expect(wrapper.find('[data-cy="datetime"]').exists()).toBe(true);
    expect(wrapper.find('[data-cy="location"]').exists()).toBe(true);

    expect(wrapper.find('[data-cy="spend-amount"]').exists()).toBe(true);
    expect(wrapper.find('[data-cy="spend-asset"]').exists()).toBe(true);

    expect(wrapper.find('[data-cy="received-amount"]').exists()).toBe(true);
    expect(wrapper.find('[data-cy="received-asset"]').exists()).toBe(true);

    expect(wrapper.find('[data-cy="unique-id"]').exists()).toBe(true);

    expect(wrapper.find('[data-cy="has-fee"]').exists()).toBe(true);
    expect((wrapper.find('[data-cy="has-fee"]').element as HTMLInputElement).checked).toBeUndefined();
    expect(wrapper.find('[data-cy="fee-amount"]').exists()).toBe(true);
    expect(wrapper.find('[data-cy="fee-asset"]').exists()).toBe(true);
    expect(wrapper.find('[data-cy="advanced-accordion"]').exists()).toBe(true);

    expect(wrapper.find('[data-cy="spend-notes"]').exists()).toBe(true);
    expect(wrapper.find('[data-cy="receive-notes"]').exists()).toBe(true);
    expect(wrapper.find('[data-cy="fee-notes"]').exists()).toBe(false);
  });

  it('should validate the form and call addHistoryEvent on save', async () => {
    vi.useFakeTimers();
    const wrapper = mount(SwapEventForm);
    vi.advanceTimersToNextTimer();
    const datetimePicker = wrapper.find('[data-cy="datetime"] input');
    const locationField = wrapper.find('[data-cy="location"] input');
    const spendAmountField = wrapper.find('[data-cy="spend-amount"] input');
    const spendAssetField = wrapper.find('[data-cy="spend-asset"] input');
    const receiveAmountField = wrapper.find('[data-cy="received-amount"] input');
    const receiveAssetField = wrapper.find('[data-cy="received-asset"] input');
    const uniqueIdField = wrapper.find('[data-cy="unique-id"] input');

    const now = dayjs();
    const nowInMs = now.valueOf();
    await datetimePicker.setValue(dayjs(nowInMs).format('DD/MM/YYYY HH:mm:ss.SSS'));
    await locationField.setValue('kraken');
    await spendAmountField.setValue('100');
    await spendAssetField.setValue('ETH');
    await receiveAmountField.setValue('0.05');
    await receiveAssetField.setValue('BTC');
    await uniqueIdField.setValue('abcd');

    vi.advanceTimersToNextTimer();

    const saveMethod = wrapper.vm.save;

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(addHistoryEventMock).toHaveBeenCalledTimes(1);
    expect(addHistoryEventMock).toHaveBeenCalledWith({
      entryType: HistoryEventEntryType.SWAP_EVENT,
      location: 'kraken',
      notes: ['', ''],
      receiveAmount: '0.05',
      receiveAsset: 'BTC',
      spendAmount: '100',
      spendAsset: 'ETH',
      timestamp: nowInMs,
      uniqueId: 'abcd',
    } satisfies AddSwapEventPayload);
    vi.useRealTimers();
  });

  it('should display validation errors when the form is invalid', async () => {
    const wrapper = mount(SwapEventForm);
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    vi.advanceTimersToNextTimer();

    expect(wrapper.find('[data-cy="location"] .details').exists()).toBe(true);
    expect(wrapper.find('[data-cy="spend-amount"] .details').exists()).toBe(true);
    expect(wrapper.find('[data-cy="spend-asset"] .details').exists()).toBe(true);
  });

  it('should enable fee-related fields when "Has Fee" checkbox is toggled', async () => {
    const wrapper = mount(SwapEventForm);

    const feeAmount = wrapper.find('[data-cy="fee-amount"] input');
    const feeAsset = wrapper.find('[data-cy="fee-asset"] input');
    const feeToggle = wrapper.find('[data-cy="has-fee"] input');

    expect(feeAmount.attributes('disabled')).toBe('');
    expect(feeAsset.attributes('disabled')).toBe('');

    await feeToggle.setValue(true);
    vi.advanceTimersToNextTimer();

    expect(feeAmount.attributes('disabled')).toBeUndefined();
    expect(feeAsset.attributes('disabled')).toBeUndefined();
    expect(wrapper.find('[data-cy="fee-notes"]').exists()).toBe(true);
  });

  it('calls editHistoryEvent when identifiers are defined', async () => {
    const wrapper = mount(SwapEventForm, {
      props: {
        data,
      },
    });

    vi.advanceTimersToNextTimer();

    const feeAmount = wrapper.find('[data-cy="fee-amount"] input');
    await feeAmount.setValue('2');

    const receiveNotes = wrapper.find('[data-cy="receive-notes"] textarea:not([aria-hidden="true"])');
    const feeNotes = wrapper.find('[data-cy="fee-notes"] textarea:not([aria-hidden="true"])');
    await receiveNotes.setValue('receive');
    await feeNotes.setValue('fee');

    vi.advanceTimersToNextTimer();

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(editHistoryEventMock).toHaveBeenCalledWith(
      expect.objectContaining({
        entryType: 'swap event',
        eventIdentifier: '24bf5c3b2031b1224d7f0e642fde058ac8316039969762b67981372229fe1a7f',
        feeAmount: '2',
        feeAsset: 'USD',
        identifier: 2737,
        location: 'binance',
        notes: ['note', 'receive', 'fee'],
        receiveAmount: '20',
        receiveAsset: 'USD',
        spendAmount: '0.01',
        spendAsset: 'ETH',
        timestamp: 1742901211000,
      }),
    );
  });

  it('should handle server validation errors', async () => {
    const wrapper = mount(SwapEventForm, {
      props: {
        data,
      },
    });

    editHistoryEventMock.mockResolvedValueOnce({
      message: { location: ['Location is required'] },
      success: false,
    });

    const saveMethod = wrapper.vm.save;

    const saveResult = await saveMethod();
    await nextTick();

    expect(saveResult).toBe(false);
    expect(wrapper.find('[data-cy="location"] .details').text()).toBe('Location is required');
  });
});
