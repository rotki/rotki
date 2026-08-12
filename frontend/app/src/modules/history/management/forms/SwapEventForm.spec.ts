import type { Pinia } from 'pinia';
import type { TradeLocationData } from '@/modules/core/common/location';
import type { AddSwapEventPayload, EditSwapEventPayload, SwapEvent } from '@/modules/history/events/schemas';
import type { GroupEventData } from '@/modules/history/management/forms/form-types';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { selectorContract } from '@test/utils/selector-contract';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { setupDayjs } from '@/modules/core/common/data/date';
import { useLocations } from '@/modules/core/common/use-locations';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';
import SwapEventForm from '@/modules/history/management/forms/SwapEventForm.vue';

vi.mock('@/modules/history/events/use-history-events', () => ({
  useHistoryEvents: vi.fn(),
}));

vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: vi.fn(),
}));

vi.mock('@/modules/assets/api/use-asset-info-api', () => ({
  useAssetInfoApi: vi.fn(),
}));

describe('forms/SwapEventForm', () => {
  let addHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>>;
  let editHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>>;
  let wrapper: VueWrapper<InstanceType<typeof SwapEventForm>>;
  let pinia: Pinia;

  const data: GroupEventData<SwapEvent> = {
    eventsInGroup: [{
      amount: bigNumberify('0.01'),
      asset: 'ETH',
      autoNotes: 'Swap 0.01 ETH in Binance',
      entryType: 'swap event',
      eventSubtype: 'spend',
      eventType: 'trade',
      extraData: null,
      groupIdentifier: '24bf5c3b2031b1224d7f0e642fde058ac8316039969762b67981372229fe1a7f',
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
      eventSubtype: 'receive',
      eventType: 'trade',
      extraData: null,
      groupIdentifier: '24bf5c3b2031b1224d7f0e642fde058ac8316039969762b67981372229fe1a7f',
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
      eventSubtype: 'fee',
      eventType: 'trade',
      extraData: null,
      groupIdentifier: '24bf5c3b2031b1224d7f0e642fde058ac8316039969762b67981372229fe1a7f',
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
    addHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>();
    editHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>();
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

    vi.mocked(useAssetInfoApi).mockReturnValue(createMock<ReturnType<typeof useAssetInfoApi>>());
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

  it('should render the documented e2e selector contract', () => {
    wrapper = createWrapper();
    // The e2e suite finds every field through these selectors; losing one is an e2e break.
    expect(selectorContract(wrapper)).toMatchInlineSnapshot(`
      [
        "data-testid=advanced-accordion",
        "data-testid=datetime",
        "data-testid=fee-add",
        "data-testid=fee-amount",
        "data-testid=fee-asset",
        "data-testid=has-fee",
        "data-testid=location",
        "data-testid=receive-notes",
        "data-testid=spend-notes",
        "data-testid=sub-event-amount[data-key=receive]",
        "data-testid=sub-event-amount[data-key=spend]",
        "data-testid=sub-event-asset[data-key=receive]",
        "data-testid=sub-event-asset[data-key=spend]",
        "data-testid=unique-id",
      ]
    `);
  });

  it('should render the form correctly', () => {
    wrapper = createWrapper();
    expect(wrapper.exists()).toBe(true);
    expect(wrapper.find('[data-testid=datetime]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=location]').exists()).toBe(true);

    expect(wrapper.find('[data-testid=sub-event-amount][data-key=spend]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=sub-event-asset][data-key=spend]').exists()).toBe(true);

    expect(wrapper.find('[data-testid=sub-event-amount][data-key=receive]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=sub-event-asset][data-key=receive]').exists()).toBe(true);

    expect(wrapper.find('[data-testid=unique-id]').exists()).toBe(true);

    expect(wrapper.find('[data-testid=has-fee]').exists()).toBe(true);
    expect(wrapper.find<HTMLInputElement>('[data-testid=has-fee]').element.checked).toBeUndefined();
    expect(wrapper.find('[data-testid=fee-add]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=advanced-accordion]').exists()).toBe(true);

    expect(wrapper.find('[data-testid=spend-notes]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=receive-notes]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=fee-notes][data-index="1"]').exists()).toBe(false);
  });

  it('should validate the form and call addHistoryEvent on save', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    const datetimePicker = wrapper.find('[data-testid=datetime] input');
    const locationField = wrapper.find('[data-testid=location] input');
    const spendAmountField = wrapper.find('[data-testid=sub-event-amount][data-key=spend] input');
    const spendAssetField = wrapper.find('[data-testid=sub-event-asset][data-key=spend] input');
    const receiveAmountField = wrapper.find('[data-testid=sub-event-amount][data-key=receive] input');
    const receiveAssetField = wrapper.find('[data-testid=sub-event-asset][data-key=receive] input');
    const uniqueIdField = wrapper.find('[data-testid=unique-id] input');

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
      fees: undefined,
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

    expect(wrapper.find('[data-testid=location] .details').exists()).toBe(true);
    expect(wrapper.find('[data-testid=sub-event-amount][data-key=spend] .details').exists()).toBe(true);
    expect(wrapper.find('[data-testid=sub-event-asset][data-key=spend] .details').exists()).toBe(true);
  });

  it('should enable fee-related fields when "Has Fee" checkbox is toggled', async () => {
    wrapper = createWrapper();

    const feeAddButton = wrapper.find('[data-testid=fee-add]');
    const feeToggle = wrapper.find('[data-testid=has-fee] input');

    expect(feeAddButton.attributes('disabled')).toBe('');

    await feeToggle.setValue(true);
    await vi.advanceTimersToNextTimerAsync();

    expect(feeAddButton.attributes('disabled')).toBeUndefined();
    expect(wrapper.find('[data-testid=fee-notes][data-index="1"]').exists()).toBe(true);
  });

  it('should call editHistoryEvent when editing an event', async () => {
    wrapper = createWrapper({
      props: {
        data,
      },
    });

    await vi.advanceTimersToNextTimerAsync();

    // Edit the fee amount in SimpleFeeEntry (existing fee from data)
    const feeAmountInputs = wrapper.findAll('[data-testid=fee-amount] input');
    expect(feeAmountInputs.length).toBeGreaterThan(0);
    await feeAmountInputs[0].setValue('2');

    const receiveNotes = wrapper.find('[data-testid=receive-notes] textarea:not([aria-hidden="true"])');
    const feeNotes = wrapper.find('[data-testid=fee-notes][data-index="1"] textarea:not([aria-hidden="true"])');
    await receiveNotes.setValue('receive');
    await feeNotes.setValue('fee');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoryEventMock.mockResolvedValueOnce({ message: '', success: false });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(editHistoryEventMock).toHaveBeenCalledWith(
      expect.objectContaining({
        entryType: 'swap event',
        fees: [{ amount: '2', asset: 'USD' }],
        identifiers: [2737, 2738, 2739],
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

  it('should handle multiple fees with individual notes', async () => {
    const dataWithMultipleFees: GroupEventData<SwapEvent> = {
      eventsInGroup: [{
        amount: bigNumberify('0.01'),
        asset: 'ETH',
        autoNotes: 'Swap 0.01 ETH in Binance',
        entryType: 'swap event',
        groupIdentifier: '24bf5c3b2031b1224d7f0e642fde058ac8316039969762b67981372229fe1a7f',
        eventSubtype: 'spend',
        eventType: 'trade',
        extraData: null,
        identifier: 2737,
        location: 'binance',
        locationLabel: null,
        sequenceIndex: 0,
        timestamp: 1742901211000,
        userNotes: 'spend note',
      }, {
        amount: bigNumberify('20'),
        asset: 'USD',
        autoNotes: 'Receive 20 USD after a swap in Binance',
        entryType: 'swap event',
        groupIdentifier: '24bf5c3b2031b1224d7f0e642fde058ac8316039969762b67981372229fe1a7f',
        eventSubtype: 'receive',
        eventType: 'trade',
        extraData: null,
        identifier: 2738,
        location: 'binance',
        locationLabel: null,
        sequenceIndex: 1,
        timestamp: 1742901211000,
        userNotes: 'receive note',
      }, {
        amount: bigNumberify('1'),
        asset: 'USD',
        autoNotes: 'Spend 1 USD as Binance swap fee',
        entryType: 'swap event',
        groupIdentifier: '24bf5c3b2031b1224d7f0e642fde058ac8316039969762b67981372229fe1a7f',
        eventSubtype: 'fee',
        eventType: 'trade',
        extraData: null,
        identifier: 2739,
        location: 'binance',
        locationLabel: null,
        sequenceIndex: 2,
        timestamp: 1742901211000,
        userNotes: 'fee note 1',
      }, {
        amount: bigNumberify('0.5'),
        asset: 'BTC',
        autoNotes: 'Spend 0.5 BTC as Binance swap fee',
        entryType: 'swap event',
        groupIdentifier: '24bf5c3b2031b1224d7f0e642fde058ac8316039969762b67981372229fe1a7f',
        eventSubtype: 'fee',
        eventType: 'trade',
        extraData: null,
        identifier: 2740,
        location: 'binance',
        locationLabel: null,
        sequenceIndex: 3,
        timestamp: 1742901211000,
        userNotes: 'fee note 2',
      }],
      type: 'edit-group',
    };

    wrapper = createWrapper({
      props: {
        data: dataWithMultipleFees,
      },
    });

    await vi.advanceTimersToNextTimerAsync();

    // Verify both fee note textareas are rendered
    expect(wrapper.find('[data-testid=fee-notes][data-index="1"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=fee-notes][data-index="2"]').exists()).toBe(true);

    // Verify fee entries are loaded
    const feeAmountInputs = wrapper.findAll('[data-testid=fee-amount] input');
    expect(feeAmountInputs).toHaveLength(2);

    // Edit the fee notes
    const feeNotes1 = wrapper.find('[data-testid=fee-notes][data-index="1"] textarea:not([aria-hidden="true"])');
    const feeNotes2 = wrapper.find('[data-testid=fee-notes][data-index="2"] textarea:not([aria-hidden="true"])');
    await feeNotes1.setValue('updated fee note 1');
    await feeNotes2.setValue('updated fee note 2');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(editHistoryEventMock).toHaveBeenCalledWith(
      expect.objectContaining({
        entryType: 'swap event',
        fees: [{ amount: '1', asset: 'USD' }, { amount: '0.5', asset: 'BTC' }],
        identifiers: [2737, 2738, 2739, 2740],
        location: 'binance',
        receiveAmount: '20',
        receiveAsset: 'USD',
        spendAmount: '0.01',
        spendAsset: 'ETH',
        timestamp: 1742901211000,
        userNotes: ['spend note', 'receive note', 'updated fee note 1', 'updated fee note 2'],
      } satisfies EditSwapEventPayload),
    );
  });

  it('should keep the seeded fees when the dialog is pointed at a group that has them', async () => {
    // The dialog reuses the form by swapping `data`, so enabling the fee through seeding must not
    // trip the has-fee watcher into replacing the rows that were just loaded.
    wrapper = createWrapper({
      props: { data: { eventsInGroup: data.eventsInGroup.slice(0, 2), type: 'edit-group' } },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.setProps({ data });
    await vi.advanceTimersToNextTimerAsync();

    // A blank value here means the watcher replaced the loaded row with an empty one.
    const feeAmount = wrapper.findAll<HTMLInputElement>('[data-testid=fee-amount] input');
    expect(feeAmount).toHaveLength(1);
    expect(feeAmount[0].element.value).toBe('1');
  });

  it('should auto-generate uniqueId when not provided on new event', async () => {
    const mockUUID = '550e8400-e29b-41d4-a716-446655440000';
    vi.spyOn(crypto, 'randomUUID').mockReturnValue(mockUUID);

    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const datetimePicker = wrapper.find('[data-testid=datetime] input');
    const locationField = wrapper.find('[data-testid=location] input');
    const spendAmountField = wrapper.find('[data-testid=sub-event-amount][data-key=spend] input');
    const spendAssetField = wrapper.find('[data-testid=sub-event-asset][data-key=spend] input');
    const receiveAmountField = wrapper.find('[data-testid=sub-event-amount][data-key=receive] input');
    const receiveAssetField = wrapper.find('[data-testid=sub-event-asset][data-key=receive] input');

    const now = dayjs();
    const nowInMs = now.valueOf();
    await datetimePicker.setValue(dayjs(nowInMs).format('DD/MM/YYYY HH:mm:ss.SSS'));
    await locationField.setValue('kraken');
    await spendAmountField.setValue('100');
    await spendAssetField.setValue('ETH');
    await receiveAmountField.setValue('0.05');
    await receiveAssetField.setValue('BTC');
    // Note: uniqueId field is left empty

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

    await wrapper.find('[data-testid=sub-event-amount][data-key=spend] input').setValue('4.5');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    const saveResult = await saveMethod();
    await nextTick();

    expect(editHistoryEventMock).toHaveBeenCalled();
    expect(saveResult).toBe(false);
    expect(wrapper.find('[data-testid=location] .details').text()).toBe('Location is required');
  });
});
