import type { AssetMap } from '@/modules/assets/types';
import type { TradeLocationData } from '@/modules/core/common/location';
import type { BitcoinEvent, EvmHistoryEvent, OnlineHistoryEvent, SolanaEvent } from '@/modules/history/events/schemas';
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
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';
import HistoryEventEntryForm from '@/modules/history/management/forms/HistoryEventEntryForm.vue';

vi.mock('json-editor-vue', () => ({
  template: '<input />',
}));

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

/** The real counterparty list unless a block stubs it, as the evm block's options test reads the real one. */
vi.mock('@/modules/history/events/mapping/use-history-event-counterparty-mappings', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/modules/history/events/mapping/use-history-event-counterparty-mappings')>();
  return { useHistoryEventCounterpartyMappings: vi.fn(original.useHistoryEventCounterpartyMappings) };
});

/** The locations an evm event can be on, which decide the kind of an event being added. */
const evmLocations = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return ref<string[]>(['ethereum', 'optimism']);
});

vi.mock('@/modules/core/common/use-supported-chains', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/modules/core/common/use-supported-chains')>();
  const vue = await import('vue');
  return {
    useSupportedChains: (): ReturnType<typeof original.useSupportedChains> => ({
      ...original.useSupportedChains(),
      txChainsToLocation: vue.computed<string[]>(() => vue.toValue(evmLocations)),
    }),
  };
});

/** How often the form reset the transaction lookup, which it does when the kind changes. */
const lookup = vi.hoisted(() => ({ resets: 0 }));

vi.mock('@/modules/history/management/forms/use-evm-tx-lookup', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/modules/history/management/forms/use-evm-tx-lookup')>();
  return {
    ...original,
    useEvmTxAutoFill: (options: Parameters<typeof original.useEvmTxAutoFill>[0]): ReturnType<typeof original.useEvmTxAutoFill> => {
      const autoFill = original.useEvmTxAutoFill(options);
      return {
        ...autoFill,
        reset: (): void => {
          lookup.resets++;
          autoFill.reset();
        },
      };
    },
  };
});

/** Moves an event being added to a location, which decides its kind. */
async function locate(wrapper: VueWrapper, location: string): Promise<void> {
  await wrapper.findComponent({ name: 'LocationSelector' }).setValue(location);
}

type FormWrapper = VueWrapper<InstanceType<typeof HistoryEventEntryForm>>;

function mountForm(pinia: Pinia, options: ComponentMountingOptions<typeof HistoryEventEntryForm> = {
  props: {
    data: { nextSequenceId: '0', type: 'add' },
  },
}): FormWrapper {
  return mount(HistoryEventEntryForm, {
    global: {
      plugins: [pinia],
      stubs: {
        I18nT: true,
      },
    },
    ...options,
  });
}

describe('forms/HistoryEventEntryForm.vue, a plain or bank event', () => {
  let wrapper: VueWrapper<InstanceType<typeof HistoryEventEntryForm>>;
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
    localStorage.clear();
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

  const createWrapper = (options: ComponentMountingOptions<typeof HistoryEventEntryForm> = {
    props: {
      data: { nextSequenceId: '0', type: 'add' },
    },
  }): VueWrapper<InstanceType<typeof HistoryEventEntryForm>> => mount(HistoryEventEntryForm, {
    global: {
      plugins: [pinia],
    },
    ...options,
  });

  it('should keep every selector the e2e suite uses', () => {
    wrapper = createWrapper();
    expect(selectorContract(wrapper)).toMatchInlineSnapshot(`
      [
        "data-testid=amount",
        "data-testid=asset",
        "data-testid=datetime",
        "data-testid=event-action-picker",
        "data-testid=event-entry-form-advance",
        "data-testid=group-identifier",
        "data-testid=grouped-amount-input-swap",
        "data-testid=location",
        "data-testid=location-label",
        "data-testid=notes",
        "data-testid=primary",
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

  it('should save a new event as a bank transaction when that entry type is picked in the dialog', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ entryType: HistoryEventEntryType.BANK_TRANSACTION_EVENT });

    await wrapper.find('[data-testid=location] input').setValue(event.location);
    await wrapper.find('[data-testid=datetime] input').setValue(dayjs(event.timestamp).format('DD/MM/YYYY HH:mm:ss.SSS'));
    wrapper.findComponent({ name: 'HistoryEventActionPicker' }).vm.$emit('update:modelValue', {
      eventSubtype: event.eventSubtype,
      eventType: event.eventType,
    });
    await nextTick();
    await wrapper.find('[data-testid=asset] input').setValue(asset.symbol);
    await wrapper.find('[data-testid=amount] input').setValue(event.amount.toString());

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    expect(await wrapper.vm.save()).toBe(true);
    expect(addHistoryEventMock).toHaveBeenCalledWith(expect.objectContaining({
      entryType: HistoryEventEntryType.BANK_TRANSACTION_EVENT,
      extraData: null,
    }));
  });

  it('should not call editHistoryEvent when nothing changed', async () => {
    wrapper = createWrapper({
      props: {
        data: { event, nextSequenceId: '1', type: 'edit' },
      },
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
      props: {
        data: { event, nextSequenceId: '1', type: 'edit' },
      },
    });
    await vi.advanceTimersToNextTimerAsync();

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoricalPriceMock.mockResolvedValueOnce(true);
    await wrapper.find('[data-testid=primary] input').setValue('1000');

    await wrapper.vm.save();
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

describe('forms/HistoryEventEntryForm.vue, an evm event', () => {
  let wrapper: VueWrapper<InstanceType<typeof HistoryEventEntryForm>>;
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
    localStorage.clear();
    vi.useFakeTimers();
    addHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>();
    editHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>();
    addHistoricalPriceMock = vi.fn<ReturnType<typeof useAssetPricesApi>['addHistoricalPrice']>();
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    vi.mocked(useLocations).mockReturnValue(createMock<ReturnType<typeof useLocations>>({
      tradeLocations: computed<TradeLocationData[]>(() => [{
        identifier: 'ethereum',
        name: 'Ethereum',
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

  const createWrapper = (options?: ComponentMountingOptions<typeof HistoryEventEntryForm>): FormWrapper => mountForm(pinia, options);

  it('should keep every selector the e2e suite uses', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await locate(wrapper, 'ethereum');
    expect(selectorContract(wrapper)).toMatchInlineSnapshot(`
      [
        "data-testid=address",
        "data-testid=amount",
        "data-testid=asset",
        "data-testid=counterparty",
        "data-testid=datetime",
        "data-testid=event-action-picker",
        "data-testid=event-entry-form-advance",
        "data-testid=group-identifier",
        "data-testid=grouped-amount-input-swap",
        "data-testid=location",
        "data-testid=location-label",
        "data-testid=notes",
        "data-testid=primary",
        "data-testid=sequence-index",
        "data-testid=tx-ref",
      ]
    `);
  });

  it('should show the default state when opening the form without any data', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await locate(wrapper, 'ethereum');

    const txRefInput = wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input');
    const locationInput = wrapper.find<HTMLInputElement>('[data-testid=location-label] input');
    const addressInput = wrapper.find<HTMLInputElement>('[data-testid=address] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');

    expect(txRefInput.element.value).toBe('');
    expect(locationInput.element.value).toBe('');
    expect(addressInput.element.value).toBe('');
    expect(sequenceIndexInput.element.value).toBe('0');
  });

  it('should update the proper fields adding an event to a group', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { group, nextSequenceId: '10', type: 'group-add' } });

    const txRefInput = wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input');
    const locationLabelInput = wrapper.find<HTMLInputElement>('[data-testid=location-label] input');
    const addressInput = wrapper.find<HTMLInputElement>('[data-testid=address] input');
    const amountInput = wrapper.find<HTMLInputElement>('[data-testid=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');
    const noteTextArea = wrapper.find<HTMLTextAreaElement>('[data-testid=notes] textarea:not([aria-hidden="true"])');

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

    const txRefInput = wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input');
    const locationLabelInput = wrapper.find<HTMLInputElement>('[data-testid=location-label] input');
    const addressInput = wrapper.find<HTMLInputElement>('[data-testid=address] input');
    const amountInput = wrapper.find<HTMLInputElement>('[data-testid=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');
    const notesTextArea = wrapper.find<HTMLTextAreaElement>('[data-testid=notes] textarea:not([aria-hidden="true"])');

    expect(txRefInput.element.value).toBe(group.txRef);
    expect(locationLabelInput.element.value).toBe(group.locationLabel);
    expect(addressInput.element.value).toBe(group.address);
    expect(amountInput.element.value).toBe(group.amount.toString());
    expect(sequenceIndexInput.element.value.replace(',', '')).toBe(group.sequenceIndex.toString());
    expect(notesTextArea.element.value).toBe(group.userNotes);
  });

  it('should show all counterparties options correctly', async () => {
    wrapper = createWrapper({ props: { data: { group, nextSequenceId: '1', type: 'group-add' } } });
    await vi.advanceTimersToNextTimerAsync();

    const { counterparties } = useHistoryEventCounterpartyMappings();

    expect(wrapper.findAll('[data-testid=counterparty] .selections span')).toHaveLength(get(counterparties).length);
  });

  it('should add a new evm event when form is submitted', async () => {
    wrapper = createWrapper();
    await nextTick();
    await vi.advanceTimersToNextTimerAsync();

    await locate(wrapper, 'ethereum');
    await wrapper.find('[data-testid=tx-ref] input').setValue(group.txRef);
    await wrapper.find('[data-testid=location-label] input').setValue(group.locationLabel);
    wrapper.findComponent({ name: 'HistoryEventActionPicker' }).vm.$emit('update:modelValue', {
      eventSubtype: group.eventSubtype || 'none',
      eventType: group.eventType,
    });
    await nextTick();
    await wrapper.find('[data-testid=asset] input').setValue(group.asset);
    await wrapper.find('[data-testid=amount] input').setValue('610'); // Using the numeric value from group.amount
    await wrapper.find('[data-testid=address] input').setValue(group.address);
    await wrapper.find('[data-testid=sequence-index] input').setValue(group.sequenceIndex);
    await wrapper.find('[data-testid=notes] textarea:not([aria-hidden="true"])').setValue(group.userNotes);
    await wrapper.find('[data-testid=datetime] input').setValue(dayjs(group.timestamp).format('DD/MM/YYYY HH:mm:ss.SSS'));

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

  it('should not call editHistoryEvent when nothing changed', async () => {
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

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoricalPriceMock.mockResolvedValueOnce(true);

    await wrapper.vm.save();
    await nextTick();
    expect(editHistoryEventMock).not.toHaveBeenCalled();
  });

  it('should not call editHistoryEvent when the historic price is the only edit', async () => {
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

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoricalPriceMock.mockResolvedValueOnce(true);
    await wrapper.find('[data-testid=primary] input').setValue('1000');

    await wrapper.vm.save();
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

    await wrapper.find('[data-testid=amount] input').setValue('650'); // Using the numeric value from group.amount
    await wrapper.find('[data-testid=sequence-index] input').setValue('2111');
    await wrapper.find('[data-testid=notes] textarea:not([aria-hidden="true"])').setValue('user note');

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

    await wrapper.find('[data-testid=amount] input').setValue('4.5');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    const saveResult = await saveMethod();
    await nextTick();

    expect(editHistoryEventMock).toHaveBeenCalled();
    expect(saveResult).toBe(false);
    expect(wrapper.find('[data-testid=location] .details').text()).toBe('invalid location');
  });

  it('should display validation errors when the form is invalid', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await locate(wrapper, 'ethereum');
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-testid=amount] .details').exists()).toBe(true);
    expect(wrapper.find('[data-testid=asset] .details').exists()).toBe(true);
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

      const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
      expect(groupIdentifierInput.element.value).toBe('ACTUAL123');
      expect(groupIdentifierInput.element.disabled).toBe(true);
    });

    it('should use groupIdentifier when actualGroupIdentifier is not present', async () => {
      wrapper = createWrapper({
        props: { data: { event: group, nextSequenceId: '10', type: 'edit' } },
      });
      await vi.advanceTimersToNextTimerAsync();

      const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
      expect(groupIdentifierInput.element.value).toBe(group.groupIdentifier);
      expect(groupIdentifierInput.element.disabled).toBe(false);
    });
  });
});

describe('forms/HistoryEventEntryForm.vue, a solana event', () => {
  let wrapper: VueWrapper<InstanceType<typeof HistoryEventEntryForm>>;
  let addHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>>;
  let editHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>>;
  let addHistoricalPriceMock: ReturnType<typeof vi.fn<ReturnType<typeof useAssetPricesApi>['addHistoricalPrice']>>;
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
    eventSubtype: '',
    eventType: 'receive',
    groupIdentifier: '10x5f2d7a2e3b4c1d6e8a9f0b3c2d1e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7',
    identifier: 14344,
    location: 'solana',
    locationLabel: '7BgBvyjrZX1YKz4oh9mjb8ZScatkkwb8DzFx7LoiVkM3',
    sequenceIndex: 2411,
    timestamp: 1686495083,
    txRef: '3ASDnpwZ3cGYMQKjsSPZHbJrJ3w8CrPzbXiLEKYLVBk1QGM1mKgXYFjXcCFqfLLu8V1r5N7vP8QcEtYYvFJYDHhx',
    userNotes: 'Receive 100 SOL from 7BgBvyjrZX1YKz4oh9mjb8ZScatkkwb8DzFx7LoiVkM3',
  };

  beforeAll(() => {
    setupDayjs();
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
    addHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>();
    editHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>();
    addHistoricalPriceMock = vi.fn<ReturnType<typeof useAssetPricesApi>['addHistoricalPrice']>();
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    vi.mocked(useLocations).mockReturnValue(createMock<ReturnType<typeof useLocations>>({
      tradeLocations: computed<TradeLocationData[]>(() => [{
        identifier: 'solana',
        name: 'Solana',
      }]),
    }));
    vi.mocked(useHistoryEvents).mockReturnValue(createMock<ReturnType<typeof useHistoryEvents>>({
      addHistoryEvent: addHistoryEventMock,
      editHistoryEvent: editHistoryEventMock,
    }));
    vi.mocked(useAssetPricesApi).mockReturnValue(createMock<ReturnType<typeof useAssetPricesApi>>({
      addHistoricalPrice: addHistoricalPriceMock,
    }));
    vi.mocked(useHistoryEventCounterpartyMappings).mockReturnValue(createMock<ReturnType<typeof useHistoryEventCounterpartyMappings>>({
      counterparties: computed<string[]>(() => [
        'test-counterparty',
        'uniswap',
      ]),
    }));
  });

  afterEach(() => {
    wrapper.unmount();
    vi.useRealTimers();
  });

  const createWrapper = (options?: ComponentMountingOptions<typeof HistoryEventEntryForm>): FormWrapper => mountForm(pinia, options);

  it('should keep every selector the e2e suite uses', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await locate(wrapper, 'solana');
    expect(selectorContract(wrapper)).toMatchInlineSnapshot(`
      [
        "data-testid=address",
        "data-testid=amount",
        "data-testid=asset",
        "data-testid=counterparty",
        "data-testid=datetime",
        "data-testid=event-action-picker",
        "data-testid=event-entry-form-advance",
        "data-testid=group-identifier",
        "data-testid=grouped-amount-input-swap",
        "data-testid=location",
        "data-testid=location-label",
        "data-testid=notes",
        "data-testid=primary",
        "data-testid=sequence-index",
        "data-testid=tx-ref",
      ]
    `);
  });

  it('should show the default state when opening the form without any data', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await locate(wrapper, 'solana');

    const txRefInput = wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input');
    const locationInput = wrapper.find<HTMLInputElement>('[data-testid=location] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');

    expect(txRefInput.element.value).toBe('');
    expect(locationInput.element.value).toBe('solana');
    expect(sequenceIndexInput.element.value).toBe('0');
  });

  it('should update the proper fields adding an event to a group', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { group, nextSequenceId: '10', type: 'group-add' } });

    const txRefInput = wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input');
    const amountInput = wrapper.find<HTMLInputElement>('[data-testid=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');
    const noteTextArea = wrapper.find<HTMLTextAreaElement>('[data-testid=notes] textarea:not([aria-hidden="true"])');

    expect(txRefInput.element.value).toBe(group.txRef);
    expect(amountInput.element.value).toBe('0');
    expect(sequenceIndexInput.element.value).toBe('10');
    expect(noteTextArea.element.value).toBe('');
  });

  it('should update the fields when editing an event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { event: group, nextSequenceId: '10', type: 'edit' } });

    const txRefInput = wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input');
    const amountInput = wrapper.find<HTMLInputElement>('[data-testid=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');
    const notesTextArea = wrapper.find<HTMLTextAreaElement>('[data-testid=notes] textarea:not([aria-hidden="true"])');

    expect(txRefInput.element.value).toBe(group.txRef);
    expect(amountInput.element.value).toBe(group.amount.toString());
    expect(sequenceIndexInput.element.value.replace(',', '')).toBe(group.sequenceIndex.toString());
    expect(notesTextArea.element.value).toBe(group.userNotes);
  });

  it('should show all counterparties options correctly', async () => {
    wrapper = createWrapper({ props: { data: { group, nextSequenceId: '1', type: 'group-add' } } });
    await vi.advanceTimersToNextTimerAsync();

    const { counterparties } = useHistoryEventCounterpartyMappings();

    expect(wrapper.findAll('[data-testid=counterparty] .selections span')).toHaveLength(get(counterparties).length);
  });

  it('should add a new solana event when form is submitted', async () => {
    wrapper = createWrapper();
    await nextTick();
    await vi.advanceTimersToNextTimerAsync();

    await locate(wrapper, 'solana');
    await wrapper.find('[data-testid=tx-ref] input').setValue(group.txRef);
    wrapper.findComponent({ name: 'HistoryEventActionPicker' }).vm.$emit('update:modelValue', {
      eventSubtype: group.eventSubtype || 'none',
      eventType: group.eventType,
    });
    await nextTick();
    await wrapper.find('[data-testid=asset] input').setValue(group.asset);
    await wrapper.find('[data-testid=amount] input').setValue('100');
    await wrapper.find('[data-testid=sequence-index] input').setValue(group.sequenceIndex);
    await wrapper.find('[data-testid=notes] textarea:not([aria-hidden="true"])').setValue(group.userNotes);
    await wrapper.find('[data-testid=datetime] input').setValue(dayjs(group.timestamp).format('DD/MM/YYYY HH:mm:ss.SSS'));

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
      eventSubtype: 'none',
      eventType: group.eventType,
      extraData: {},
      groupIdentifier: null,
      locationLabel: null,
      sequenceIndex: group.sequenceIndex.toString(),
      timestamp: group.timestamp,
      txRef: group.txRef,
      userNotes: group.userNotes,
    });
  });

  it('should not call editHistoryEvent when nothing changed', async () => {
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

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoricalPriceMock.mockResolvedValueOnce(true);

    await wrapper.vm.save();
    await nextTick();
    expect(editHistoryEventMock).not.toHaveBeenCalled();
  });

  it('should not call editHistoryEvent when the historic price is the only edit', async () => {
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

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoricalPriceMock.mockResolvedValueOnce(true);
    await wrapper.find('[data-testid=primary] input').setValue('1000');

    await wrapper.vm.save();
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

    await wrapper.find('[data-testid=amount] input').setValue('150');
    await wrapper.find('[data-testid=sequence-index] input').setValue('2111');
    await wrapper.find('[data-testid=notes] textarea:not([aria-hidden="true"])').setValue('user note');

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(editHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(editHistoryEventMock).toHaveBeenCalledWith({
      address: group.address ?? null,
      amount: bigNumberify('150'),
      asset: group.asset,
      counterparty: '',
      entryType: HistoryEventEntryType.SOLANA_EVENT,
      eventSubtype: 'none',
      eventType: group.eventType,
      extraData: {},
      groupIdentifier: group.groupIdentifier,
      identifier: group.identifier,
      locationLabel: group.locationLabel ?? null,
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

    await wrapper.find('[data-testid=amount] input').setValue('200');

    editHistoryEventMock.mockResolvedValueOnce({
      message: { amount: ['amount too large'] },
      success: false,
    });

    const saveMethod = wrapper.vm.save;

    const saveResult = await saveMethod();
    await nextTick();

    expect(editHistoryEventMock).toHaveBeenCalled();
    expect(saveResult).toBe(false);
    expect(wrapper.find('[data-testid=amount] .details').text()).toBe('amount too large');
  });

  it('should display validation errors when the form is invalid', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await locate(wrapper, 'solana');
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-testid=amount] .details').exists()).toBe(true);
    expect(wrapper.find('[data-testid=asset] .details').exists()).toBe(true);
  });

  describe('actualGroupIdentifier', () => {
    const eventWithActualGroupIdentifier: SolanaEvent = {
      ...group,
      actualGroupIdentifier: 'ACTUAL123',
      groupIdentifier: 'LINKED456',
    };

    it('should use actualGroupIdentifier when present and disable the field', async () => {
      wrapper = createWrapper({
        props: { data: { event: eventWithActualGroupIdentifier, nextSequenceId: '1', type: 'edit' } },
      });
      await vi.advanceTimersToNextTimerAsync();

      await wrapper.find('[data-testid=event-entry-form-advance] [data-accordion-trigger]').trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
      expect(groupIdentifierInput.element.value).toBe('ACTUAL123');
      expect(groupIdentifierInput.element.disabled).toBe(true);
    });

    it('should use groupIdentifier when actualGroupIdentifier is not present', async () => {
      wrapper = createWrapper({
        props: { data: { event: group, nextSequenceId: '1', type: 'edit' } },
      });
      await vi.advanceTimersToNextTimerAsync();

      await wrapper.find('[data-testid=event-entry-form-advance] [data-accordion-trigger]').trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
      expect(groupIdentifierInput.element.value).toBe(group.groupIdentifier);
      expect(groupIdentifierInput.element.disabled).toBe(false);
    });
  });
});

describe('forms/HistoryEventEntryForm.vue, a bitcoin event', () => {
  let wrapper: VueWrapper<InstanceType<typeof HistoryEventEntryForm>>;
  let addHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>>;
  let editHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>>;
  let addHistoricalPriceMock: ReturnType<typeof vi.fn<ReturnType<typeof useAssetPricesApi>['addHistoricalPrice']>>;
  let pinia: Pinia;

  const asset = {
    assetType: 'own chain',
    isCustomAsset: false,
    name: 'Bitcoin',
    symbol: 'BTC',
  };

  const mapping: AssetMap = {
    assetCollections: {},
    assets: { [asset.symbol]: asset },
  };

  const group: BitcoinEvent = {
    address: null,
    amount: bigNumberify(100),
    asset: asset.symbol,
    counterparty: null,
    entryType: HistoryEventEntryType.BITCOIN_EVENT,
    eventSubtype: '',
    eventType: 'receive',
    groupIdentifier: 'btc_e47f43692083b6b4bb3d4d6150acd3c016b09fb841e4055e1f5bb8ad44858bc6',
    identifier: 14344,
    location: 'bitcoin',
    locationLabel: 'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4',
    sequenceIndex: 2411,
    timestamp: 1686495083,
    txRef: 'e47f43692083b6b4bb3d4d6150acd3c016b09fb841e4055e1f5bb8ad44858bc6',
    userNotes: 'Receive 100 BTC from 1G3MiaKdccQmiTr4gYSKmrCVDaLQ5nvBRp',
  };

  beforeAll(() => {
    setupDayjs();
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
    addHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>();
    editHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>();
    addHistoricalPriceMock = vi.fn<ReturnType<typeof useAssetPricesApi>['addHistoricalPrice']>();
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    vi.mocked(useLocations).mockReturnValue(createMock<ReturnType<typeof useLocations>>({
      tradeLocations: computed<TradeLocationData[]>(() => [{
        identifier: 'bitcoin',
        name: 'Bitcoin',
      }, {
        identifier: 'bitcoin_cash',
        name: 'Bitcoin Cash',
      }]),
    }));
    vi.mocked(useHistoryEvents).mockReturnValue(createMock<ReturnType<typeof useHistoryEvents>>({
      addHistoryEvent: addHistoryEventMock,
      editHistoryEvent: editHistoryEventMock,
    }));
    vi.mocked(useAssetPricesApi).mockReturnValue(createMock<ReturnType<typeof useAssetPricesApi>>({
      addHistoricalPrice: addHistoricalPriceMock,
    }));
    vi.mocked(useHistoryEventCounterpartyMappings).mockReturnValue(createMock<ReturnType<typeof useHistoryEventCounterpartyMappings>>({
      counterparties: computed<string[]>(() => [
        'test-counterparty',
        'uniswap',
      ]),
    }));
  });

  afterEach(() => {
    wrapper.unmount();
    vi.useRealTimers();
  });

  const createWrapper = (options?: ComponentMountingOptions<typeof HistoryEventEntryForm>): FormWrapper => mountForm(pinia, options);

  it('should keep every selector the e2e suite uses', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await locate(wrapper, 'bitcoin');
    expect(selectorContract(wrapper)).toMatchInlineSnapshot(`
      [
        "data-testid=amount",
        "data-testid=asset",
        "data-testid=counterparty",
        "data-testid=datetime",
        "data-testid=event-action-picker",
        "data-testid=event-entry-form-advance",
        "data-testid=group-identifier",
        "data-testid=grouped-amount-input-swap",
        "data-testid=location",
        "data-testid=location-label",
        "data-testid=notes",
        "data-testid=primary",
        "data-testid=sequence-index",
        "data-testid=tx-ref",
      ]
    `);
  });

  it('should show the default state when opening the form without any data', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await locate(wrapper, 'bitcoin');

    const txRefInput = wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input');
    const locationInput = wrapper.find<HTMLInputElement>('[data-testid=location] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');

    expect(txRefInput.element.value).toBe('');
    expect(locationInput.element.value).toBe('bitcoin');
    expect(sequenceIndexInput.element.value).toBe('0');
  });

  it('should update the proper fields adding an event to a group', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { group, nextSequenceId: '10', type: 'group-add' } });

    const txRefInput = wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input');
    const amountInput = wrapper.find<HTMLInputElement>('[data-testid=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');
    const noteTextArea = wrapper.find<HTMLTextAreaElement>('[data-testid=notes] textarea:not([aria-hidden="true"])');

    expect(txRefInput.element.value).toBe(group.txRef);
    expect(amountInput.element.value).toBe('0');
    expect(sequenceIndexInput.element.value).toBe('10');
    expect(noteTextArea.element.value).toBe('');
  });

  it('should update the fields when editing an event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { event: group, nextSequenceId: '10', type: 'edit' } });

    const txRefInput = wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input');
    const amountInput = wrapper.find<HTMLInputElement>('[data-testid=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');
    const notesTextArea = wrapper.find<HTMLTextAreaElement>('[data-testid=notes] textarea:not([aria-hidden="true"])');

    expect(txRefInput.element.value).toBe(group.txRef);
    expect(amountInput.element.value).toBe(group.amount.toString());
    expect(sequenceIndexInput.element.value.replace(',', '')).toBe(group.sequenceIndex.toString());
    expect(notesTextArea.element.value).toBe(group.userNotes);
  });

  it('should lock the location to the saved transaction outside the add flow, since the location picks the asset and a BTC event could otherwise be relabelled BCH', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-testid=location] input').attributes('disabled')).toBeUndefined();

    for (const data of [
      { event: group, nextSequenceId: '10', type: 'edit' },
      { group, nextSequenceId: '10', type: 'group-add' },
    ] as const) {
      await wrapper.setProps({ data });
      await vi.advanceTimersToNextTimerAsync();

      expect(wrapper.find('[data-testid=location] input').attributes('disabled')).toBeDefined();
      expect(wrapper.find('[data-testid=tx-ref] input').attributes('disabled')).toBeDefined();
    }
  });

  it('should show all counterparties options correctly', async () => {
    wrapper = createWrapper({ props: { data: { group, nextSequenceId: '1', type: 'group-add' } } });
    await vi.advanceTimersToNextTimerAsync();

    const { counterparties } = useHistoryEventCounterpartyMappings();

    expect(wrapper.findAll('[data-testid=counterparty] .selections span')).toHaveLength(get(counterparties).length);
  });

  it('should add a new bitcoin event when form is submitted', async () => {
    wrapper = createWrapper();
    await nextTick();
    await vi.advanceTimersToNextTimerAsync();

    await locate(wrapper, 'bitcoin');
    await wrapper.find('[data-testid=tx-ref] input').setValue(group.txRef);
    wrapper.findComponent({ name: 'HistoryEventActionPicker' }).vm.$emit('update:modelValue', {
      eventSubtype: group.eventSubtype || 'none',
      eventType: group.eventType,
    });
    await nextTick();
    // the asset is not picked, it follows the location
    await wrapper.find('[data-testid=amount] input').setValue('100');
    await wrapper.find('[data-testid=sequence-index] input').setValue(group.sequenceIndex);
    await wrapper.find('[data-testid=notes] textarea:not([aria-hidden="true"])').setValue(group.userNotes);
    await wrapper.find('[data-testid=datetime] input').setValue(dayjs(group.timestamp).format('DD/MM/YYYY HH:mm:ss.SSS'));

    const saveMethod = wrapper.vm.save;

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(addHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(addHistoryEventMock).toHaveBeenCalledWith({
      amount: group.amount,
      asset: group.asset,
      counterparty: '',
      entryType: HistoryEventEntryType.BITCOIN_EVENT,
      eventSubtype: 'none',
      eventType: group.eventType,
      extraData: {},
      groupIdentifier: null,
      location: group.location,
      locationLabel: null,
      sequenceIndex: group.sequenceIndex.toString(),
      timestamp: group.timestamp,
      txRef: group.txRef,
      userNotes: group.userNotes,
    });
  });

  it('should not call editHistoryEvent when nothing changed', async () => {
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

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoricalPriceMock.mockResolvedValueOnce(true);

    await wrapper.vm.save();
    await nextTick();
    expect(editHistoryEventMock).not.toHaveBeenCalled();
  });

  it('should not call editHistoryEvent when the historic price is the only edit', async () => {
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

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoricalPriceMock.mockResolvedValueOnce(true);
    await wrapper.find('[data-testid=primary] input').setValue('1000');

    await wrapper.vm.save();
    await nextTick();
    expect(editHistoryEventMock).not.toHaveBeenCalled();
  });

  it('should edit an existing bitcoin event when form is submitted', async () => {
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

    await wrapper.find('[data-testid=amount] input').setValue('150');
    await wrapper.find('[data-testid=sequence-index] input').setValue('2111');
    await wrapper.find('[data-testid=notes] textarea:not([aria-hidden="true"])').setValue('user note');

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(editHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(editHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify('150'),
      asset: group.asset,
      counterparty: '',
      entryType: HistoryEventEntryType.BITCOIN_EVENT,
      eventSubtype: 'none',
      eventType: group.eventType,
      extraData: {},
      groupIdentifier: group.groupIdentifier,
      identifier: group.identifier,
      location: group.location,
      locationLabel: group.locationLabel ?? null,
      sequenceIndex: '2111',
      timestamp: group.timestamp,
      txRef: group.txRef,
      userNotes: 'user note',
    });
  });

  it('should keep the location and asset of the edited event', async () => {
    wrapper = createWrapper({
      props: {
        data: {
          event: {
            ...group,
            asset: 'BCH',
            groupIdentifier: `bch_${group.txRef}`,
            location: 'bitcoin_cash',
          },
          nextSequenceId: '1',
          type: 'edit',
        },
      },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-testid=amount] input').setValue('150');

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    expect(await wrapper.vm.save()).toBe(true);
    expect(editHistoryEventMock).toHaveBeenCalledWith(expect.objectContaining({
      asset: 'BCH',
      location: 'bitcoin_cash',
    }));
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

    await wrapper.find('[data-testid=amount] input').setValue('200');

    editHistoryEventMock.mockResolvedValueOnce({
      message: { amount: ['amount too large'] },
      success: false,
    });

    const saveMethod = wrapper.vm.save;

    const saveResult = await saveMethod();
    await nextTick();

    expect(editHistoryEventMock).toHaveBeenCalled();
    expect(saveResult).toBe(false);
    expect(wrapper.find('[data-testid=amount] .details').text()).toBe('amount too large');
  });

  it('should display validation errors when the form is invalid', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await locate(wrapper, 'bitcoin');
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-testid=amount] .details').exists()).toBe(true);
    // the asset field has nothing to validate since it follows the location
    expect(wrapper.find('[data-testid=tx-ref] .details').exists()).toBe(true);
  });

  describe('actualGroupIdentifier', () => {
    const eventWithActualGroupIdentifier: BitcoinEvent = {
      ...group,
      actualGroupIdentifier: 'ACTUAL123',
      groupIdentifier: 'LINKED456',
    };

    it('should use actualGroupIdentifier when present and disable the field', async () => {
      wrapper = createWrapper({
        props: { data: { event: eventWithActualGroupIdentifier, nextSequenceId: '1', type: 'edit' } },
      });
      await vi.advanceTimersToNextTimerAsync();

      await wrapper.find('[data-testid=event-entry-form-advance] [data-accordion-trigger]').trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
      expect(groupIdentifierInput.element.value).toBe('ACTUAL123');
      expect(groupIdentifierInput.element.disabled).toBe(true);
    });

    it('should use groupIdentifier when actualGroupIdentifier is not present', async () => {
      wrapper = createWrapper({
        props: { data: { event: group, nextSequenceId: '1', type: 'edit' } },
      });
      await vi.advanceTimersToNextTimerAsync();

      await wrapper.find('[data-testid=event-entry-form-advance] [data-accordion-trigger]').trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
      expect(groupIdentifierInput.element.value).toBe(group.groupIdentifier);
      expect(groupIdentifierInput.element.disabled).toBe(false);
    });
  });
});

describe('forms/HistoryEventEntryForm.vue, the kind of an event being added', () => {
  const evmTxRef = '0x4ba949779d936631dc9eb68fa9308c18de51db253aeea919384c728942f95ba9';
  const signature = '5wHu1qwD4kLwYqCEuNqTvhpFvGYRVYVEHVsdvR2v3Wg7fFyGxUWJTgL4wZ3Y1sM9RcYnPbLXZhKUqLNvV7kA8dQz';

  let wrapper: FormWrapper;
  let addHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>>;
  let editHistoryEventMock: ReturnType<typeof vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>>;
  let pinia: Pinia;

  const evmEvent: EvmHistoryEvent = {
    address: null,
    amount: bigNumberify(1),
    asset: 'ETH',
    counterparty: null,
    entryType: HistoryEventEntryType.EVM_EVENT,
    eventSubtype: 'none',
    eventType: 'receive',
    groupIdentifier: `10${evmTxRef}`,
    identifier: 7,
    location: 'base',
    locationLabel: null,
    sequenceIndex: 1,
    timestamp: 1686495083,
    txRef: evmTxRef,
  };

  beforeAll(() => {
    setupDayjs();
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
    set(evmLocations, ['ethereum', 'optimism']);
    addHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>().mockResolvedValue({ success: true });
    editHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>().mockResolvedValue({ success: true });
    vi.mocked(useLocations).mockReturnValue(createMock<ReturnType<typeof useLocations>>({
      tradeLocations: computed<TradeLocationData[]>(() => [{ identifier: 'kraken', name: 'Kraken' }]),
    }));
    vi.mocked(useHistoryEvents).mockReturnValue(createMock<ReturnType<typeof useHistoryEvents>>({
      addHistoryEvent: addHistoryEventMock,
      editHistoryEvent: editHistoryEventMock,
    }));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  async function createWrapper(options?: ComponentMountingOptions<typeof HistoryEventEntryForm>): Promise<FormWrapper> {
    wrapper = mountForm(pinia, options);
    await vi.advanceTimersToNextTimerAsync();
    return wrapper;
  }

  function has(testid: string): boolean {
    return wrapper.find(`[data-testid=${testid}]`).exists();
  }

  it('should start as a plain event, with its group identifier where a chain event has its reference', async () => {
    await createWrapper();

    expect(has('group-identifier')).toBe(true);
    expect(has('tx-ref')).toBe(false);
    expect(has('counterparty')).toBe(false);
  });

  it.each([
    { location: 'optimism', reference: 'tx-ref' },
    { location: 'solana', reference: 'tx-ref' },
    { location: 'bitcoin', reference: 'tx-ref' },
    { location: 'kraken', reference: 'group-identifier' },
  ])('should ask for the $reference of an event on $location', async ({ location, reference }) => {
    await createWrapper();
    await locate(wrapper, location);

    expect(has(reference)).toBe(true);
  });

  it('should open a new event as the kind of the last location picked', async () => {
    await createWrapper();
    await locate(wrapper, 'solana');
    wrapper.unmount();

    await createWrapper();

    expect(has('tx-ref')).toBe(true);
    expect(wrapper.findComponent({ name: 'LocationSelector' }).props('modelValue')).toBe('solana');
  });

  it('should clear an evm hash moving to solana', async () => {
    await createWrapper();
    await locate(wrapper, 'ethereum');
    await wrapper.find('[data-testid=tx-ref] input').setValue(evmTxRef);

    await locate(wrapper, 'solana');

    expect(wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input').element.value).toBe('');
  });

  it('should not flag the signature a move to solana emptied, until it is touched', async () => {
    await createWrapper();
    await locate(wrapper, 'ethereum');
    await wrapper.find('[data-testid=tx-ref] input').setValue(evmTxRef);
    await wrapper.find('[data-testid=tx-ref] input').trigger('blur');

    await locate(wrapper, 'solana');
    expect(wrapper.find('[data-testid=tx-ref] .details').text()).toBe('');

    await wrapper.find('[data-testid=tx-ref] input').trigger('blur');
    expect(wrapper.find('[data-testid=tx-ref] .details').text()).not.toBe('');
  });

  it('should make an event picked on an evm chain an evm event once the chains load', async () => {
    set(evmLocations, []);
    await createWrapper();
    await locate(wrapper, 'ethereum');
    expect(has('tx-ref')).toBe(false);

    set(evmLocations, ['ethereum']);
    await nextTick();

    expect(has('tx-ref')).toBe(true);
  });

  it('should keep a new bank transaction a bank transaction on any location', async () => {
    await createWrapper({ props: { data: { nextSequenceId: '0', type: 'add' }, entryType: HistoryEventEntryType.BANK_TRANSACTION_EVENT } });
    await locate(wrapper, 'ethereum');

    expect(has('tx-ref')).toBe(false);
    expect(has('group-identifier')).toBe(true);
  });

  it('should follow the picker from a bank transaction back to a history event on a chain', async () => {
    await createWrapper({ props: { data: { nextSequenceId: '0', type: 'add' }, entryType: HistoryEventEntryType.BANK_TRANSACTION_EVENT } });
    await locate(wrapper, 'ethereum');

    await wrapper.setProps({ entryType: HistoryEventEntryType.HISTORY_EVENT });

    expect(has('tx-ref')).toBe(true);
  });

  it('should reset the transaction lookup when the kind changes, and keep it moving between two evm chains', async () => {
    await createWrapper();
    await locate(wrapper, 'ethereum');
    const resets = lookup.resets;

    await locate(wrapper, 'optimism');
    expect(lookup.resets).toBe(resets);

    await locate(wrapper, 'solana');
    expect(lookup.resets).toBe(resets + 1);
  });

  it('should keep an edited event the kind it was saved as, on a location that would imply another', async () => {
    await createWrapper({ props: { data: { event: { ...evmEvent, location: 'ethereum' }, nextSequenceId: '1', type: 'edit' } } });
    await wrapper.setProps({ data: { event: evmEvent, nextSequenceId: '1', type: 'edit' } });
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.find('[data-testid=amount] input').setValue('2');

    await expect(wrapper.vm.save()).resolves.toBe(true);
    expect(editHistoryEventMock.mock.calls[0][0]).toMatchObject({ entryType: HistoryEventEntryType.EVM_EVENT, location: 'base' });
  });

  it('should add into a solana transaction as a solana event, with the location locked', async () => {
    const solanaGroup: SolanaEvent = {
      address: null,
      amount: bigNumberify(1),
      asset: 'SOL',
      counterparty: null,
      entryType: HistoryEventEntryType.SOLANA_EVENT,
      eventSubtype: 'none',
      eventType: 'receive',
      groupIdentifier: `solana${signature}`,
      identifier: 9,
      location: 'solana',
      locationLabel: null,
      sequenceIndex: 0,
      timestamp: 1686495083,
      txRef: signature,
    };
    await createWrapper({ props: { data: { group: solanaGroup, nextSequenceId: '3', type: 'group-add' } } });

    expect(wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input').element.value).toBe(signature);
    expect(wrapper.find<HTMLInputElement>('[data-testid=location] input').element.disabled).toBe(true);
  });
});
