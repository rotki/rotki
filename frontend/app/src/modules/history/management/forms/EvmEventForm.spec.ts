import type { AssetMap } from '@/types/asset';
import type { EvmHistoryEvent } from '@/types/history/events/schemas';
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
import { useHistoryEventProductMappings } from '@/composables/history/events/mapping/product';
import { useLocations } from '@/composables/locations';
import EvmEventForm from '@/modules/history/management/forms/EvmEventForm.vue';
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

describe('forms/EvmEventForm.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof EvmEventForm>>;
  let addHistoryEventMock: ReturnType<typeof vi.fn>;
  let editHistoryEventMock: ReturnType<typeof vi.fn>;
  let addHistoricalPriceMock: ReturnType<typeof vi.fn>;
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
    eventIdentifier: '10x4ba949779d936631dc9eb68fa9308c18de51db253aeea919384c728942f95ba9',
    eventSubtype: '',
    eventType: 'receive',
    identifier: 14344,
    location: 'ethereum',
    locationLabel: '0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8',
    product: null,
    sequenceIndex: 2411,
    timestamp: 1686495083,
    txHash: '0x4ba949779d936631dc9eb68fa9308c18de51db253aeea919384c728942f95ba9',
    userNotes:
      'Receive 610 Visit https://rafts.cc to claim rewards. from 0x30a2EBF10f34c6C4874b0bDD5740690fD2f3B70C to 0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8',
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
        identifier: 'ethereum',
        name: 'Ethereum',
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

  const createWrapper = (options: ComponentMountingOptions<typeof EvmEventForm> = {
    props: {
      data: { nextSequenceId: '0', type: 'add' },
    },
  }): VueWrapper<InstanceType<typeof EvmEventForm>> =>
    mount(EvmEventForm, {
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

    const txHashInput = wrapper.find<HTMLInputElement>('[data-cy=tx-hash] input');
    const locationInput = wrapper.find<HTMLInputElement>('[data-cy=location-label] input');
    const addressInput = wrapper.find<HTMLInputElement>('[data-cy=address] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');

    expect(txHashInput.element.value).toBe('');
    expect(locationInput.element.value).toBe('');
    expect(addressInput.element.value).toBe('');
    expect(sequenceIndexInput.element.value).toBe('0');
  });

  it('should update the proper fields adding an event to a group', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { group, nextSequenceId: '10', type: 'group-add' } });

    const txHashInput = wrapper.find<HTMLInputElement>('[data-cy=tx-hash] input');
    const locationLabelInput = wrapper.find<HTMLInputElement>('[data-cy=location-label] input');
    const addressInput = wrapper.find<HTMLInputElement>('[data-cy=address] input');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');
    const noteTextArea = wrapper.find<HTMLTextAreaElement>('[data-cy=notes] textarea:not([aria-hidden="true"])');

    expect(txHashInput.element.value).toBe(group.txHash);
    expect(locationLabelInput.element.value).toBe(group.locationLabel);
    expect(addressInput.element.value).toBe(group.address);
    expect(amountInput.element.value).toBe('0');
    expect(sequenceIndexInput.element.value).toBe('10');
    expect(noteTextArea.element.value).toBe('');
  });

  it('it should update the fields when editing an event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { event: group, nextSequenceId: '10', type: 'edit' } });

    const txHashInput = wrapper.find<HTMLInputElement>('[data-cy=tx-hash] input');
    const locationLabelInput = wrapper.find<HTMLInputElement>('[data-cy=location-label] input');
    const addressInput = wrapper.find<HTMLInputElement>('[data-cy=address] input');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');
    const notesTextArea = wrapper.find<HTMLTextAreaElement>('[data-cy=notes] textarea:not([aria-hidden="true"])');

    expect(txHashInput.element.value).toBe(group.txHash);
    expect(locationLabelInput.element.value).toBe(group.locationLabel);
    expect(addressInput.element.value).toBe(group.address);
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

  it('should show product options, based on selected counterparty', async () => {
    wrapper = createWrapper({ props: { data: { group, nextSequenceId: '1', type: 'group-add' } } });
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-cy=product] input').attributes('disabled')).toBe('');

    // input is still disabled if the counterparty doesn't have mapped products.
    await wrapper.find('[data-cy=counterparty] input').setValue('1inch');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-cy=product] input').attributes('disabled')).toBe('');

    // the product options should be displayed correctly if the counterparty has mapped products.
    const selectedCounterparty = 'convex';
    await wrapper.find('[data-cy=counterparty] input').setValue(selectedCounterparty);
    await vi.advanceTimersToNextTimerAsync();

    const { historyEventProductsMapping } = useHistoryEventProductMappings();

    const products = get(historyEventProductsMapping)[selectedCounterparty];

    const spans = wrapper.findAll('[data-cy=product] .selections span');
    expect(spans).toHaveLength(products.length);

    for (let i = 0; i < products.length; i++) expect(products.includes(spans.at(i)!.text())).toBeTruthy();
  });

  it('should add a new evm event when form is submitted', async () => {
    wrapper = createWrapper();
    await nextTick();
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-cy=tx-hash] input').setValue(group.txHash);
    await wrapper.find('[data-cy=location] input').setValue(group.location);
    await wrapper.find('[data-cy=location-label] input').setValue(group.locationLabel);
    await wrapper.find('[data-cy=eventType] input').setValue(group.eventType);
    await wrapper.find('[data-cy=asset] input').setValue(group.asset);
    await wrapper.find('[data-cy=amount] input').setValue('610'); // Using the numeric value from group.amount
    await wrapper.find('[data-cy=address] input').setValue(group.address);
    await wrapper.find('[data-cy=sequence-index] input').setValue(group.sequenceIndex);
    await wrapper.find('[data-cy=notes] textarea:not([aria-hidden="true"])').setValue(group.userNotes);
    await wrapper.find('[data-cy=datetime] input').setValue(dayjs(group.timestamp).format('DD/MM/YYYY HH:mm:ss.SSS'));

    if (group.counterparty) {
      await wrapper.find('[data-cy=counterparty] input').setValue(group.counterparty);
    }

    if (group.product) {
      await wrapper.find('[data-cy=product] input').setValue(group.product);
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
      address: group.address,
      amount: group.amount,
      asset: group.asset,
      counterparty: group.counterparty,
      entryType: HistoryEventEntryType.EVM_EVENT,
      eventIdentifier: null,
      eventSubtype: 'none',
      eventType: group.eventType,
      extraData: {},
      location: group.location,
      locationLabel: group.locationLabel,
      product: group.product,
      sequenceIndex: group.sequenceIndex.toString(),
      timestamp: group.timestamp,
      txHash: group.txHash,
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

    await wrapper.find('[data-cy=amount] input').setValue('650'); // Using the numeric value from group.amount
    await wrapper.find('[data-cy=sequence-index] input').setValue('2111');
    await wrapper.find('[data-cy=notes] textarea:not([aria-hidden="true"])').setValue('user note');

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
      eventIdentifier: group.eventIdentifier,
      eventSubtype: 'none',
      eventType: group.eventType,
      extraData: {},
      identifier: group.identifier,
      location: group.location,
      locationLabel: group.locationLabel,
      product: group.product,
      sequenceIndex: '2111',
      timestamp: group.timestamp,
      txHash: group.txHash,
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
