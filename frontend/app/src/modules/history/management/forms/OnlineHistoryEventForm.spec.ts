import type { AssetMap } from '@/types/asset';
import type { OnlineHistoryEvent } from '@/types/history/events/schemas';
import type { TradeLocationData } from '@/types/history/trade/location';
import { bigNumberify, HistoryEventEntryType, One } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { nextTick } from 'vue';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { useHistoryEvents } from '@/composables/history/events';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { useLocations } from '@/composables/locations';
import OnlineHistoryEventForm from '@/modules/history/management/forms/OnlineHistoryEventForm.vue';
import { usePriceTaskManager } from '@/modules/prices/use-price-task-manager';
import { setupDayjs } from '@/utils/date';

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

describe('forms/OnlineHistoryEventForm.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof OnlineHistoryEventForm>>;
  let addHistoryEventMock: ReturnType<typeof vi.fn>;
  let editHistoryEventMock: ReturnType<typeof vi.fn>;
  let addHistoricalPriceMock: ReturnType<typeof vi.fn>;
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

  const event: OnlineHistoryEvent = {
    amount: bigNumberify(10),
    asset: asset.symbol,
    entryType: HistoryEventEntryType.HISTORY_EVENT,
    eventSubtype: 'reward',
    eventType: 'staking',
    groupIdentifier: 'STJ6KRHJYGA',
    identifier: 449,
    location: 'kraken',
    locationLabel: 'Kraken 1',
    sequenceIndex: 20,
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
    (useHistoryEvents as Mock).mockReturnValue({
      addHistoryEvent: addHistoryEventMock,
      editHistoryEvent: editHistoryEventMock,
    });
    (useLocations as Mock).mockReturnValue({
      tradeLocations: computed<TradeLocationData[]>(() => [{
        identifier: 'kraken',
        name: 'Kraken',
      }]),
    });
    (useAssetPricesApi as Mock).mockReturnValue({
      addHistoricalPrice: addHistoricalPriceMock,
    });
  });

  afterEach(() => {
    wrapper.unmount();
    vi.useRealTimers();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof OnlineHistoryEventForm> = {
    props: {
      data: { nextSequenceId: '0', type: 'add' },
    },
  }): VueWrapper<InstanceType<typeof OnlineHistoryEventForm>> => mount(OnlineHistoryEventForm, {
    global: {
      plugins: [pinia],
    },
    ...options,
  });

  it('should show the default state when adding a new event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-cy=groupIdentifier] input');
    const locationLabel = wrapper.find<HTMLInputElement>('[data-cy=locationLabel] .input-value');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');

    expect(groupIdentifierInput.element.value).toBe('');
    expect(locationLabel.element.value).toBe('');
    expect(sequenceIndexInput.element.value).toBe('0');
  });

  it('should update the fields when adding an event in an existing group', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({
      data: { group: event, nextSequenceId: '10', type: 'group-add' },
    });
    await vi.advanceTimersToNextTimerAsync();

    const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-cy=groupIdentifier] input');
    const locationLabelInput = wrapper.find<HTMLInputElement>('[data-cy=locationLabel] .input-value');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');
    const noteTextArea = wrapper.find<HTMLTextAreaElement>('[data-cy=notes] textarea:not([aria-hidden="true"])');

    expect(groupIdentifierInput.element.value).toBe(event.groupIdentifier);
    expect(locationLabelInput.element.value).toBe(event.locationLabel);
    expect(amountInput.element.value).toBe('0');
    expect(sequenceIndexInput.element.value).toBe('10');
    expect(noteTextArea.element.value).toBe('');
  });

  it('should update the fields when editing an event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({
      data: { event, nextSequenceId: '10', type: 'edit' },
    });
    await vi.advanceTimersToNextTimerAsync();

    const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-cy=groupIdentifier] input');
    const locationLabelInput = wrapper.find<HTMLInputElement>('[data-cy=locationLabel] .input-value');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');
    const noteTextArea = wrapper.find<HTMLTextAreaElement>('[data-cy=notes] textarea:not([aria-hidden="true"])');

    expect(groupIdentifierInput.element.value).toBe(event.groupIdentifier);
    expect(locationLabelInput.element.value).toBe(event.locationLabel);
    expect(amountInput.element.value).toBe(event.amount.toString());
    expect(sequenceIndexInput.element.value.replace(',', '')).toBe(event.sequenceIndex.toString());
    expect(noteTextArea.element.value).toBe(event.userNotes);
  });

  it('should show all eventTypes options correctly', async () => {
    wrapper = createWrapper({ props: { data: { group: event, nextSequenceId: '1', type: 'group-add' } } });
    await vi.advanceTimersToNextTimerAsync();

    const { historyEventTypesData } = useHistoryEventMappings();

    expect(wrapper.findAll('[data-cy=eventType] .selections span')).toHaveLength(get(historyEventTypesData).length);
  });

  it('should show all eventSubTypes options correctly', async () => {
    wrapper = createWrapper({ props: { data: { group: event, nextSequenceId: '1', type: 'group-add' } } });
    await vi.advanceTimersToNextTimerAsync();

    const { historyEventSubTypesData } = useHistoryEventMappings();

    expect(wrapper.findAll('[data-cy=eventSubtype] .selections span')).toHaveLength(
      get(historyEventSubTypesData).length,
    );
  });

  it('should show correct eventSubtypes options, based on selected eventType', async () => {
    wrapper = createWrapper({ props: { data: { group: event, nextSequenceId: '1', type: 'group-add' } } });
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

  it('should add a new online event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-cy=groupIdentifier] input').setValue(event.groupIdentifier);
    await wrapper.find('[data-cy=location] input').setValue(event.location);
    await wrapper.find('[data-cy=locationLabel] input').setValue(event.locationLabel);
    await wrapper.find('[data-cy=datetime] input').setValue(dayjs(event.timestamp).format('DD/MM/YYYY HH:mm:ss.SSS'));
    await wrapper.find('[data-cy=eventType] input').setValue(event.eventType);
    await wrapper.find('[data-cy=eventSubtype] input').setValue(event.eventSubtype);
    await wrapper.find('[data-cy=asset] input').setValue(asset.symbol);
    await wrapper.find('[data-cy=amount] input').setValue(event.amount.toString());
    await wrapper.find('[data-cy=sequence-index] input').setValue(event.sequenceIndex.toString());
    await wrapper.find('[data-cy=notes] textarea:not([aria-hidden="true"])').setValue(event.userNotes);

    const saveMethod = wrapper.vm.save;

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(addHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(addHistoryEventMock).toHaveBeenCalledWith({
      amount: event.amount,
      asset: event.asset,
      entryType: HistoryEventEntryType.HISTORY_EVENT,
      eventSubtype: event.eventSubtype,
      eventType: event.eventType,
      groupIdentifier: event.groupIdentifier,
      location: event.location,
      locationLabel: event.locationLabel,
      sequenceIndex: event.sequenceIndex.toString(),
      timestamp: event.timestamp,
      userNotes: event.userNotes,
    });
  });

  it('should not call editHistoryEvent when only updating the historic price', async () => {
    wrapper = createWrapper({
      props: {
        data: { event, nextSequenceId: '1', type: 'edit' },
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

  it('should edit an existing online event', async () => {
    wrapper = createWrapper({
      props: {
        data: { event, nextSequenceId: '1', type: 'edit' },
      },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-cy=asset] input').setValue('USD');
    await wrapper.find('[data-cy=amount] input').setValue('50');

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(editHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(editHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify(50),
      asset: 'USD',
      entryType: HistoryEventEntryType.HISTORY_EVENT,
      eventSubtype: event.eventSubtype,
      eventType: event.eventType,
      groupIdentifier: event.groupIdentifier,
      identifier: event.identifier,
      location: event.location,
      locationLabel: event.locationLabel,
      sequenceIndex: event.sequenceIndex.toString(),
      timestamp: event.timestamp,
      userNotes: event.userNotes,
    });
  });

  it('should handle server validation errors', async () => {
    wrapper = createWrapper({
      props: {
        data: {
          event,
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
});
