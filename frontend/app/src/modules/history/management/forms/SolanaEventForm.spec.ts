import type { AssetMap } from '@/types/asset';
import type { SolanaEvent } from '@/types/history/events/schemas';
import type { TradeLocationData } from '@/types/history/trade/location';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { nextTick } from 'vue';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { useHistoryEvents } from '@/composables/history/events';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';
import { useLocations } from '@/composables/locations';
import SolanaEventForm from '@/modules/history/management/forms/SolanaEventForm.vue';
import { setupDayjs } from '@/utils/date';

vi.mock('json-editor-vue', () => ({
  template: '<input />',
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

vi.mock('@/composables/history/events/mapping/counterparty', () => ({
  useHistoryEventCounterpartyMappings: vi.fn(),
}));

describe('forms/SolanaEventForm.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof SolanaEventForm>>;
  let addHistoryEventMock: ReturnType<typeof vi.fn>;
  let editHistoryEventMock: ReturnType<typeof vi.fn>;
  let addHistoricalPriceMock: ReturnType<typeof vi.fn>;
  let pinia: Pinia;

  const asset = {
    assetType: 'own chain',
    isCustomAsset: false,
    name: 'Solana',
    symbol: 'SOL',
  };

  const mapping: AssetMap = {
    assetCollections: {},
    assets: { [asset.symbol]: asset },
  };

  const group: SolanaEvent = {
    address: 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
    amount: bigNumberify(100),
    asset: asset.symbol,
    counterparty: null,
    entryType: HistoryEventEntryType.SOLANA_EVENT,
    eventIdentifier: '10x5f2d7a2e3b4c1d6e8a9f0b3c2d1e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7',
    eventSubtype: '',
    eventType: 'receive',
    identifier: 14344,
    location: 'solana',
    locationLabel: '7BgBvyjrZX1YKz4oh9mjb8ZScatkkwb8DzFx7LoiVkM3',
    sequenceIndex: 2411,
    timestamp: 1686495083000,
    txRef: '3ASDnpwZ3cGYMQKjsSPZHbJrJ3w8CrPzbXiLEKYLVBk1QGM1mKgXYFjXcCFqfLLu8V1r5N7vP8QcEtYYvFJYDHhx',
    userNotes: 'Receive 100 SOL from 7BgBvyjrZX1YKz4oh9mjb8ZScatkkwb8DzFx7LoiVkM3',
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
    (useLocations as Mock).mockReturnValue({
      tradeLocations: computed<TradeLocationData[]>(() => [{
        identifier: 'solana',
        name: 'Solana',
      }]),
    });
    (useHistoryEvents as Mock).mockReturnValue({
      addHistoryEvent: addHistoryEventMock,
      editHistoryEvent: editHistoryEventMock,
    });
    (useAssetPricesApi as Mock).mockReturnValue({
      addHistoricalPrice: addHistoricalPriceMock,
    });
    (useHistoryEventCounterpartyMappings as Mock).mockReturnValue({
      counterparties: computed(() => [
        { identifier: 'test-counterparty', label: 'Test Counterparty' },
        { identifier: 'uniswap', label: 'Uniswap' },
      ]),
    });
  });

  afterEach(() => {
    wrapper.unmount();
    vi.useRealTimers();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof SolanaEventForm> = {
    props: {
      data: { nextSequenceId: '0', type: 'add' },
    },
  }): VueWrapper<InstanceType<typeof SolanaEventForm>> =>
    mount(SolanaEventForm, {
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
    const locationInput = wrapper.find<HTMLInputElement>('[data-cy=location] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');

    expect(txRefInput.element.value).toBe('');
    expect(locationInput.element.value).toBe('solana');
    expect(sequenceIndexInput.element.value).toBe('0');
  });

  it('should update the proper fields adding an event to a group', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { group, nextSequenceId: '10', type: 'group-add' } });

    const txRefInput = wrapper.find<HTMLInputElement>('[data-cy=tx-ref] input');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');
    const noteTextArea = wrapper.find<HTMLTextAreaElement>('[data-cy=notes] textarea:not([aria-hidden="true"])');

    expect(txRefInput.element.value).toBe(group.txRef);
    expect(amountInput.element.value).toBe('0');
    expect(sequenceIndexInput.element.value).toBe('10');
    expect(noteTextArea.element.value).toBe('');
  });

  it('it should update the fields when editing an event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { event: group, nextSequenceId: '10', type: 'edit' } });

    const txRefInput = wrapper.find<HTMLInputElement>('[data-cy=tx-ref] input');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');
    const notesTextArea = wrapper.find<HTMLTextAreaElement>('[data-cy=notes] textarea:not([aria-hidden="true"])');

    expect(txRefInput.element.value).toBe(group.txRef);
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
      expect(keysFromGlobalMappings.includes(spans.at(i)!.text())).toBeTruthy();
  });

  it('should add a new solana event when form is submitted', async () => {
    wrapper = createWrapper();
    await nextTick();
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-cy=tx-ref] input').setValue(group.txRef);
    await wrapper.find('[data-cy=location] input').setValue(group.location);
    await wrapper.find('[data-cy=eventType] input').setValue(group.eventType);
    await wrapper.find('[data-cy=asset] input').setValue(group.asset);
    await wrapper.find('[data-cy=amount] input').setValue('100');
    await wrapper.find('[data-cy=sequence-index] input').setValue(group.sequenceIndex);
    await wrapper.find('[data-cy=notes] textarea:not([aria-hidden="true"])').setValue(group.userNotes);
    await wrapper.find('[data-cy=datetime] input').setValue(dayjs(group.timestamp).format('DD/MM/YYYY HH:mm:ss.SSS'));

    if (group.counterparty) {
      await wrapper.find('[data-cy=counterparty] input').setValue(group.counterparty);
    }

    if (group.eventSubtype) {
      await wrapper.find('[data-cy=eventSubtype] input').setValue(group.eventSubtype);
    }

    const saveMethod = wrapper.vm.save;

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(addHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(addHistoryEventMock).toHaveBeenCalledWith({
      address: null,
      amount: group.amount,
      asset: group.asset,
      counterparty: '',
      entryType: HistoryEventEntryType.SOLANA_EVENT,
      eventIdentifier: null,
      eventSubtype: 'none',
      eventType: group.eventType,
      extraData: {},
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

  it('should edit an existing solana event when form is submitted', async () => {
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

    await wrapper.find('[data-cy=amount] input').setValue('150');
    await wrapper.find('[data-cy=sequence-index] input').setValue('2111');
    await wrapper.find('[data-cy=notes] textarea:not([aria-hidden="true"])').setValue('user note');

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(editHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(editHistoryEventMock).toHaveBeenCalledWith({
      address: group.address || null,
      amount: bigNumberify('150'),
      asset: group.asset,
      counterparty: '',
      entryType: HistoryEventEntryType.SOLANA_EVENT,
      eventIdentifier: group.eventIdentifier,
      eventSubtype: 'none',
      eventType: group.eventType,
      extraData: {},
      identifier: group.identifier,
      locationLabel: group.locationLabel || null,
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
    await vi.advanceTimersToNextTimerAsync();

    // Change a field to make the form dirty
    await wrapper.find('[data-cy=amount] input').setValue('200');

    editHistoryEventMock.mockResolvedValueOnce({
      message: { amount: ['amount too large'] },
      success: false,
    });

    const saveMethod = wrapper.vm.save;

    const saveResult = await saveMethod();
    await nextTick();

    expect(editHistoryEventMock).toHaveBeenCalled();
    expect(saveResult).toBe(false);
    expect(wrapper.find('[data-cy=amount] .details').text()).toBe('amount too large');
  });

  it('should display validation errors when the form is invalid', async () => {
    wrapper = createWrapper();
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-cy=amount] .details').exists()).toBe(true);
    expect(wrapper.find('[data-cy=asset] .details').exists()).toBe(true);
  });
});
