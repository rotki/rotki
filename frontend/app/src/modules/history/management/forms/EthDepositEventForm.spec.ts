import type { AssetMap } from '@/types/asset';
import type { EthDepositEvent } from '@/types/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { nextTick } from 'vue';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { useHistoryEvents } from '@/composables/history/events';
import EthDepositEventForm from '@/modules/history/management/forms/EthDepositEventForm.vue';
import { setupDayjs } from '@/utils/date';

vi.mock('json-editor-vue', () => ({
  template: '<input />',
}));

vi.mock('@/composables/history/events', () => ({
  useHistoryEvents: vi.fn(),
}));

vi.mock('@/composables/api/assets/prices', () => ({
  useAssetPricesApi: vi.fn().mockReturnValue({
    addHistoricalPrice: vi.fn(),
  }),
}));

describe('form/EthDepositEventForm.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof EthDepositEventForm>>;
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

  const event: EthDepositEvent = {
    address: '0x00000000219ab540356cBB839Cbe05303d7705Fa',
    amount: bigNumberify('3.2'),
    asset: asset.symbol,
    counterparty: 'eth2',
    entryType: HistoryEventEntryType.ETH_DEPOSIT_EVENT,
    eventIdentifier: '10x3849ac4b278cac18f0e52a7d1a1dc1c14b1b4f50d6c11087e9a6591fd7b62d08',
    eventSubtype: 'deposit asset',
    eventType: 'staking',
    identifier: 11344,
    location: 'ethereum',
    locationLabel: '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    product: 'staking',
    sequenceIndex: 12,
    timestamp: 1697522243000,
    txHash: '0x3849ac4b278cac18f0e52a7d1a1dc1c14b1b4f50d6c11087e9a6591fd7b62d08',
    userNotes: 'Deposit 3.2 ETH to validator 223',
    validatorIndex: 223,
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

  const createWrapper = (options: ComponentMountingOptions<typeof EthDepositEventForm> = {
    props: {
      data: { nextSequenceId: '0', type: 'add' },
    },
  }): VueWrapper<InstanceType<typeof EthDepositEventForm>> =>
    mount(EthDepositEventForm, {
      global: {
        plugins: [pinia],
      },
      ...options,
    });

  it('should show the default state when adding a new event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-cy=eth-deposit-event-form__advance] .accordion__header').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    const validatorIndexInput = wrapper.find<HTMLInputElement>('[data-cy=validatorIndex] input');
    const txHashInput = wrapper.find<HTMLInputElement>('[data-cy=tx-hash] input');
    const eventIdentifierInput = wrapper.find<HTMLInputElement>('[data-cy=eventIdentifier] input');
    const depositorInput = wrapper.find<HTMLInputElement>('[data-cy=depositor] .input-value');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');

    expect(validatorIndexInput.element.value).toBe('');
    expect(txHashInput.element.value).toBe('');
    expect(eventIdentifierInput.element.value).toBe('');
    expect(depositorInput.element.value).toBe('');
    expect(sequenceIndexInput.element.value).toBe('0');
  });

  it('should update when data adding a new event in a group', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { group: event, nextSequenceId: '10', type: 'group-add' } });

    await wrapper.find('[data-cy=eth-deposit-event-form__advance] .accordion__header').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    const validatorIndexInput = wrapper.find<HTMLInputElement>('[data-cy=validatorIndex] input');
    const txHashInput = wrapper.find<HTMLInputElement>('[data-cy=tx-hash] input');
    const eventIdentifierInput = wrapper.find<HTMLInputElement>('[data-cy=eventIdentifier] input');
    const depositorInput = wrapper.find<HTMLInputElement>('[data-cy=depositor] .input-value');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');

    expect(validatorIndexInput.element.value).toBe(event.validatorIndex.toString());
    expect(txHashInput.element.value).toBe(event.txHash);
    expect(eventIdentifierInput.element.value).toBe(event.eventIdentifier);
    expect(depositorInput.element.value).toBe(event.locationLabel);
    expect(amountInput.element.value).toBe('0');
    expect(sequenceIndexInput.element.value).toBe('10');
  });

  it('it should update the fields when editing an event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { event, nextSequenceId: '1', type: 'edit' } });

    await wrapper.find('[data-cy=eth-deposit-event-form__advance] .accordion__header').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    const validatorIndexInput = wrapper.find<HTMLInputElement>('[data-cy=validatorIndex] input');
    const txHashInput = wrapper.find<HTMLInputElement>('[data-cy=tx-hash] input');
    const eventIdentifierInput = wrapper.find<HTMLInputElement>('[data-cy=eventIdentifier] input');
    const depositorInput = wrapper.find<HTMLInputElement>('[data-cy=depositor] .input-value');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');

    expect(validatorIndexInput.element.value).toBe(event.validatorIndex.toString());
    expect(txHashInput.element.value).toBe(event.txHash);
    expect(eventIdentifierInput.element.value).toBe(event.eventIdentifier);
    expect(depositorInput.element.value).toBe(event.locationLabel);
    expect(amountInput.element.value).toBe(event.amount.toString());
    expect(sequenceIndexInput.element.value.replace(',', '')).toBe(event.sequenceIndex.toString());
  });

  it('should add a new deposit event when form is submitted', async () => {
    wrapper = createWrapper();
    await nextTick();
    await vi.advanceTimersToNextTimerAsync();

    const now = dayjs();
    const nowInMs = now.valueOf();

    await wrapper.find('[data-cy=amount] input').setValue('2.5');
    await wrapper.find('[data-cy=tx-hash] input').setValue('0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef');
    await wrapper.find('[data-cy=validatorIndex] input').setValue('123');
    await wrapper.find('[data-cy=depositor] .input-value').setValue('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12');
    await wrapper.find('[data-cy=sequence-index] input').setValue('5');
    await wrapper.find<HTMLInputElement>('[data-cy=datetime] input').setValue(dayjs(nowInMs).format('DD/MM/YYYY HH:mm:ss.SSS'));

    const saveMethod = wrapper.vm.save;

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(addHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(addHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify('2.5'),
      depositor: '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
      entryType: HistoryEventEntryType.ETH_DEPOSIT_EVENT,
      eventIdentifier: null,
      extraData: {},
      sequenceIndex: '5',
      timestamp: nowInMs,
      txHash: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
      validatorIndex: 123,
    });
  });

  it('should not call editHistoryEvent when only updating the historic price', async () => {
    wrapper = createWrapper({
      props: {
        data: {
          event,
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

  it('should edit an existing deposit event when form is submitted', async () => {
    wrapper = createWrapper({
      props: {
        data: {
          event,
          nextSequenceId: '1',
          type: 'edit',
        },
      },
    });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-cy=amount] input').setValue('4.5');
    await wrapper.find('[data-cy=validatorIndex] input').setValue('224');

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(editHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(editHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify('4.5'),
      depositor: event.locationLabel,
      entryType: HistoryEventEntryType.ETH_DEPOSIT_EVENT,
      eventIdentifier: event.eventIdentifier,
      extraData: {},
      identifier: event.identifier,
      sequenceIndex: event.sequenceIndex.toString(),
      timestamp: event.timestamp,
      txHash: event.txHash,
      validatorIndex: 224,
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
      message: { txHash: ['transaction hash is required'] },
      success: false,
    });

    await wrapper.find('[data-cy=validatorIndex] input').setValue('123123');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    const saveResult = await saveMethod();
    await nextTick();

    expect(editHistoryEventMock).toHaveBeenCalled();
    expect(saveResult).toBe(false);
    expect(wrapper.find('[data-cy=tx-hash] .details').text()).toBe('transaction hash is required');
  });

  it('should display validation errors when the form is invalid', async () => {
    wrapper = createWrapper();
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-cy=depositor] .details').exists()).toBe(true);
    expect(wrapper.find('[data-cy=validatorIndex] .details').exists()).toBe(true);
    expect(wrapper.find('[data-cy=tx-hash] .details').exists()).toBe(true);
  });
});
