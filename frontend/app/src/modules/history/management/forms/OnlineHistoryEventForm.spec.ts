import type { AssetMap } from '@/modules/assets/types';
import type { TradeLocationData } from '@/modules/core/common/location';
import type { OnlineHistoryEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType, One } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { selectorContract } from '@test/utils/selector-contract';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { setupDayjs } from '@/modules/core/common/data/date';
import { useLocations } from '@/modules/core/common/use-locations';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';
import OnlineHistoryEventForm from '@/modules/history/management/forms/OnlineHistoryEventForm.vue';

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

describe('forms/OnlineHistoryEventForm.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof OnlineHistoryEventForm>>;
  let addHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>>;
  let editHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>>;
  let addHistoricalPriceMock: ReturnType<typeof vi.fn<ReturnType<typeof useAssetPricesApi>['addHistoricalPrice']>>;
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
    addHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>();
    editHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>();
    addHistoricalPriceMock = vi.fn<ReturnType<typeof useAssetPricesApi>['addHistoricalPrice']>();
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    vi.mocked(usePriceTaskManager().getHistoricPrice).mockResolvedValue(One);
    vi.mocked(useHistoryEvents).mockReturnValue(createMock<ReturnType<typeof useHistoryEvents>>({
      addHistoryEvent: addHistoryEventMock,
      editHistoryEvent: editHistoryEventMock,
    }));
    vi.mocked(useLocations).mockReturnValue(createMock<ReturnType<typeof useLocations>>({
      tradeLocations: computed<TradeLocationData[]>(() => [{
        identifier: 'kraken',
        name: 'Kraken',
      }]),
    }));
    vi.mocked(useAssetPricesApi).mockReturnValue(createMock<ReturnType<typeof useAssetPricesApi>>({
      addHistoricalPrice: addHistoricalPriceMock,
    }));
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

  it('should render the documented e2e selector contract', () => {
    wrapper = createWrapper();
    // The e2e suite finds every field through these selectors; losing one is an e2e break.
    expect(selectorContract(wrapper)).toMatchInlineSnapshot(`
      [
        "data-testid=amount",
        "data-testid=asset",
        "data-testid=datetime",
        "data-testid=event-action-picker",
        "data-testid=group-identifier",
        "data-testid=grouped-amount-input-swap",
        "data-testid=location",
        "data-testid=location-label",
        "data-testid=notes",
        "data-testid=primary",
        "data-testid=secondary",
        "data-testid=sequence-index",
      ]
    `);
  });

  it('should show the default state when adding a new event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
    const locationLabel = wrapper.find<HTMLInputElement>('[data-testid=location-label] .input-value');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');

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

    const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
    const locationLabelInput = wrapper.find<HTMLInputElement>('[data-testid=location-label] .input-value');
    const amountInput = wrapper.find<HTMLInputElement>('[data-testid=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');
    const noteTextArea = wrapper.find<HTMLTextAreaElement>('[data-testid=notes] textarea:not([aria-hidden="true"])');

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

    const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
    const locationLabelInput = wrapper.find<HTMLInputElement>('[data-testid=location-label] .input-value');
    const amountInput = wrapper.find<HTMLInputElement>('[data-testid=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');
    const noteTextArea = wrapper.find<HTMLTextAreaElement>('[data-testid=notes] textarea:not([aria-hidden="true"])');

    expect(groupIdentifierInput.element.value).toBe(event.groupIdentifier);
    expect(locationLabelInput.element.value).toBe(event.locationLabel);
    expect(amountInput.element.value).toBe(event.amount.toString());
    expect(sequenceIndexInput.element.value.replace(',', '')).toBe(event.sequenceIndex.toString());
    expect(noteTextArea.element.value).toBe(event.userNotes);
  });

  it('should add a new online event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-testid=group-identifier] input').setValue(event.groupIdentifier);
    await wrapper.find('[data-testid=location] input').setValue(event.location);
    await wrapper.find('[data-testid=location-label] input').setValue(event.locationLabel);
    await wrapper.find('[data-testid=datetime] input').setValue(dayjs(event.timestamp).format('DD/MM/YYYY HH:mm:ss.SSS'));
    wrapper.findComponent({ name: 'HistoryEventActionPicker' }).vm.$emit('update:modelValue', {
      eventSubtype: event.eventSubtype,
      eventType: event.eventType,
    });
    await nextTick();
    await wrapper.find('[data-testid=asset] input').setValue(asset.symbol);
    await wrapper.find('[data-testid=amount] input').setValue(event.amount.toString());
    await wrapper.find('[data-testid=sequence-index] input').setValue(event.sequenceIndex.toString());
    await wrapper.find('[data-testid=notes] textarea:not([aria-hidden="true"])').setValue(event.userNotes);

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

  it('should edit an existing online event', async () => {
    wrapper = createWrapper({
      props: {
        data: { event, nextSequenceId: '1', type: 'edit' },
      },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-testid=asset] input').setValue('USD');
    await wrapper.find('[data-testid=amount] input').setValue('50');

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

    await wrapper.find('[data-testid=amount] input').setValue('4.5');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    const saveResult = await saveMethod();
    await nextTick();

    expect(editHistoryEventMock).toHaveBeenCalled();
    expect(saveResult).toBe(false);
    expect(wrapper.find('[data-testid=location] .details').text()).toBe('invalid location');
  });

  it('should auto-generate groupIdentifier when not provided on new event', async () => {
    const mockUUID = '550e8400-e29b-41d4-a716-446655440000';
    vi.spyOn(crypto, 'randomUUID').mockReturnValue(mockUUID);

    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-testid=location] input').setValue(event.location);
    await wrapper.find('[data-testid=datetime] input').setValue(dayjs(event.timestamp).format('DD/MM/YYYY HH:mm:ss.SSS'));
    wrapper.findComponent({ name: 'HistoryEventActionPicker' }).vm.$emit('update:modelValue', {
      eventSubtype: event.eventSubtype,
      eventType: event.eventType,
    });
    await nextTick();
    await wrapper.find('[data-testid=asset] input').setValue(asset.symbol);
    await wrapper.find('[data-testid=amount] input').setValue(event.amount.toString());
    // Note: groupIdentifier field is left empty

    await vi.advanceTimersToNextTimerAsync();

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await wrapper.vm.save();
    expect(saveResult).toBe(true);
    expect(addHistoryEventMock).toHaveBeenCalledWith(
      expect.objectContaining({
        groupIdentifier: mockUUID,
      }),
    );
  });

  it('should display validation errors when the form is invalid', async () => {
    wrapper = createWrapper();
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-testid=amount] .details').exists()).toBe(true);
    expect(wrapper.find('[data-testid=asset] .details').exists()).toBe(true);
  });

  describe('actualGroupIdentifier', () => {
    const eventWithActualGroupIdentifier: OnlineHistoryEvent = {
      ...event,
      actualGroupIdentifier: 'ACTUAL123',
      groupIdentifier: 'LINKED456',
    };

    it('should use actualGroupIdentifier when present and disable the field', async () => {
      wrapper = createWrapper({
        props: { data: { event: eventWithActualGroupIdentifier, nextSequenceId: '1', type: 'edit' } },
      });
      await vi.advanceTimersToNextTimerAsync();

      const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
      expect(groupIdentifierInput.element.value).toBe('ACTUAL123');
      expect(groupIdentifierInput.element.disabled).toBe(true);
    });

    it('should use groupIdentifier when actualGroupIdentifier is not present', async () => {
      wrapper = createWrapper({
        props: { data: { event, nextSequenceId: '1', type: 'edit' } },
      });
      await vi.advanceTimersToNextTimerAsync();

      const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
      expect(groupIdentifierInput.element.value).toBe(event.groupIdentifier);
      // Note: groupIdentifier is always disabled in edit mode for this form (data.type !== 'add')
      expect(groupIdentifierInput.element.disabled).toBe(true);
    });
  });
});
