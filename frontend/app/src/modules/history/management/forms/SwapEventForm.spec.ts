import type { DependentEventData } from '@/modules/history/management/forms/form-types';
import type { AddSwapEventPayload, EditSwapEventPayload, SwapEvent } from '@/types/history/events';
import type { TradeLocationData } from '@/types/history/trade/location';
import type { Pinia } from 'pinia';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useHistoryEvents } from '@/composables/history/events';
import { useLocations } from '@/composables/locations';
import SwapEventForm from '@/modules/history/management/forms/SwapEventForm.vue';
import { useMessageStore } from '@/store/message';
import { setupDayjs } from '@/utils/date';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
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
  let wrapper: VueWrapper<InstanceType<typeof SwapEventForm>>;
  let pinia: Pinia;

  const data: DependentEventData<SwapEvent> = {
    eventsInGroup: [{
      amount: bigNumberify('0.01'),
      asset: 'ETH',
      autoNotes: 'Swap 0.01 ETH in Binance',
      entryType: 'swap event',
      eventIdentifier: '24bf5c3b2031b1224d7f0e642fde058ac8316039969762b67981372229fe1a7f',
      eventSubtype: 'spend',
      eventType: 'trade',
      extraData: null,
      identifier: 2737,
      location: 'binance',
      locationLabel: null,
      sequenceIndex: 0,
      timestamp: 1742901211000,
      userNotes: 'note',
    }, {
      amount: bigNumberify('20'),
      asset: 'USD',
      autoNotes: 'Receive 20 USD after a swap in Binance',
      entryType: 'swap event',
      eventIdentifier: '24bf5c3b2031b1224d7f0e642fde058ac8316039969762b67981372229fe1a7f',
      eventSubtype: 'receive',
      eventType: 'trade',
      extraData: null,
      identifier: 2738,
      location: 'binance',
      locationLabel: null,
      sequenceIndex: 1,
      timestamp: 1742901211000,
      userNotes: '',
    }, {
      amount: bigNumberify('1'),
      asset: 'USD',
      autoNotes: 'Spend 1 USD as Binance swap fee',
      entryType: 'swap event',
      eventIdentifier: '24bf5c3b2031b1224d7f0e642fde058ac8316039969762b67981372229fe1a7f',
      eventSubtype: 'fee',
      eventType: 'trade',
      extraData: null,
      identifier: 2739,
      location: 'binance',
      locationLabel: null,
      sequenceIndex: 2,
      timestamp: 1742901211000,
      userNotes: '',
    }],
    type: 'edit-group',
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
    wrapper.unmount();
    vi.useRealTimers();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof SwapEventForm> = {
    props: {
      data: { nextSequenceId: '0', type: 'add' },
    },
  }): VueWrapper<InstanceType<typeof SwapEventForm>> => mount(SwapEventForm, {
    global: {
      plugins: [pinia],
    },
    ...options,
  });

  it('should render the form correctly', () => {
    wrapper = createWrapper();
    expect(wrapper.exists()).toBe(true);
    expect(wrapper.find('[data-cy=datetime]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=location]').exists()).toBe(true);

    expect(wrapper.find('[data-cy=spend-amount]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=spend-asset]').exists()).toBe(true);

    expect(wrapper.find('[data-cy=received-amount]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=received-asset]').exists()).toBe(true);

    expect(wrapper.find('[data-cy=unique-id]').exists()).toBe(true);

    expect(wrapper.find('[data-cy=has-fee]').exists()).toBe(true);
    expect((wrapper.find('[data-cy=has-fee]').element as HTMLInputElement).checked).toBeUndefined();
    expect(wrapper.find('[data-cy=fee-amount]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=fee-asset]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=advanced-accordion]').exists()).toBe(true);

    expect(wrapper.find('[data-cy=spend-notes]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=receive-notes]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=fee-notes]').exists()).toBe(false);
  });

  it('should validate the form and call addHistoryEvent on save', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    const datetimePicker = wrapper.find('[data-cy=datetime] input');
    const locationField = wrapper.find('[data-cy=location] input');
    const spendAmountField = wrapper.find('[data-cy=spend-amount] input');
    const spendAssetField = wrapper.find('[data-cy=spend-asset] input');
    const receiveAmountField = wrapper.find('[data-cy=received-amount] input');
    const receiveAssetField = wrapper.find('[data-cy=received-asset] input');
    const uniqueIdField = wrapper.find('[data-cy=unique-id] input');

    const now = dayjs();
    const nowInMs = now.valueOf();
    await datetimePicker.setValue(dayjs(nowInMs).format('DD/MM/YYYY HH:mm:ss.SSS'));
    await locationField.setValue('kraken');
    await spendAmountField.setValue('100');
    await spendAssetField.setValue('ETH');
    await receiveAmountField.setValue('0.05');
    await receiveAssetField.setValue('BTC');
    await uniqueIdField.setValue('abcd');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(addHistoryEventMock).toHaveBeenCalledTimes(1);
    expect(addHistoryEventMock).toHaveBeenCalledWith({
      entryType: HistoryEventEntryType.SWAP_EVENT,
      location: 'kraken',
      receiveAmount: '0.05',
      receiveAsset: 'BTC',
      spendAmount: '100',
      spendAsset: 'ETH',
      timestamp: nowInMs,
      uniqueId: 'abcd',
      userNotes: ['', ''],
    } satisfies AddSwapEventPayload);
    vi.useRealTimers();
  });

  it('should display validation errors when the form is invalid', async () => {
    wrapper = createWrapper();
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-cy=location] .details').exists()).toBe(true);
    expect(wrapper.find('[data-cy=spend-amount] .details').exists()).toBe(true);
    expect(wrapper.find('[data-cy=spend-asset] .details').exists()).toBe(true);
  });

  it('should enable fee-related fields when "Has Fee" checkbox is toggled', async () => {
    wrapper = createWrapper();

    const feeAmount = wrapper.find('[data-cy=fee-amount] input');
    const feeAsset = wrapper.find('[data-cy=fee-asset] input');
    const feeToggle = wrapper.find('[data-cy=has-fee] input');

    expect(feeAmount.attributes('disabled')).toBe('');
    expect(feeAsset.attributes('disabled')).toBe('');

    await feeToggle.setValue(true);
    await vi.advanceTimersToNextTimerAsync();

    expect(feeAmount.attributes('disabled')).toBeUndefined();
    expect(feeAsset.attributes('disabled')).toBeUndefined();
    expect(wrapper.find('[data-cy=fee-notes]').exists()).toBe(true);
  });

  it('calls editHistoryEvent when editing an event', async () => {
    wrapper = createWrapper({
      props: {
        data,
      },
    });

    await vi.advanceTimersToNextTimerAsync();

    const feeAmount = wrapper.find('[data-cy=fee-amount] input');
    await feeAmount.setValue('2');

    const receiveNotes = wrapper.find('[data-cy=receive-notes] textarea:not([aria-hidden="true"])');
    const feeNotes = wrapper.find('[data-cy=fee-notes] textarea:not([aria-hidden="true"])');
    await receiveNotes.setValue('receive');
    await feeNotes.setValue('fee');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoryEventMock.mockResolvedValueOnce({ success: false });

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
        receiveAmount: '20',
        receiveAsset: 'USD',
        spendAmount: '0.01',
        spendAsset: 'ETH',
        timestamp: 1742901211000,
        userNotes: ['note', 'receive', 'fee'],
      } satisfies EditSwapEventPayload),
    );
    expect(addHistoryEventMock).toHaveBeenCalledTimes(0);
  });

  it('should handle server validation errors', async () => {
    wrapper = createWrapper({
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
    expect(wrapper.find('[data-cy=location] .details').text()).toBe('Location is required');
  });
});
