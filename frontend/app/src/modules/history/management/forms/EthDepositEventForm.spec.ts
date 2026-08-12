import type { AssetMap } from '@/modules/assets/types';
import type { EthDepositEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { selectorContract } from '@test/utils/selector-contract';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { setupDayjs } from '@/modules/core/common/data/date';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';
import EthDepositEventForm from '@/modules/history/management/forms/EthDepositEventForm.vue';

vi.mock('@/modules/history/events/use-history-events', () => ({
  useHistoryEvents: vi.fn(),
}));

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: vi.fn().mockReturnValue({
    addHistoricalPrice: vi.fn(),
  }),
}));

describe('form/EthDepositEventForm.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof EthDepositEventForm>>;
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

  const event: EthDepositEvent = {
    address: '0x00000000219ab540356cBB839Cbe05303d7705Fa',
    amount: bigNumberify('3.2'),
    asset: asset.symbol,
    counterparty: 'eth2',
    entryType: HistoryEventEntryType.ETH_DEPOSIT_EVENT,
    eventSubtype: 'deposit asset',
    eventType: 'staking',
    groupIdentifier: '10x3849ac4b278cac18f0e52a7d1a1dc1c14b1b4f50d6c11087e9a6591fd7b62d08',
    identifier: 11344,
    location: 'ethereum',
    locationLabel: '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    sequenceIndex: 12,
    timestamp: 1697522243000,
    txRef: '0x3849ac4b278cac18f0e52a7d1a1dc1c14b1b4f50d6c11087e9a6591fd7b62d08',
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
    addHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['addHistoryEvent']>();
    editHistoryEventMock = vi.fn<ReturnType<typeof useHistoryEvents>['editHistoryEvent']>();
    addHistoricalPriceMock = vi.fn<ReturnType<typeof useAssetPricesApi>['addHistoricalPrice']>();
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
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

  it('should render the documented e2e selector contract', () => {
    wrapper = createWrapper();
    // The e2e suite finds every field through these selectors; losing one is an e2e break.
    expect(selectorContract(wrapper)).toMatchInlineSnapshot(`
      [
        "data-testid=amount",
        "data-testid=asset",
        "data-testid=datetime",
        "data-testid=depositor",
        "data-testid=eth-deposit-event-form__advance",
        "data-testid=group-identifier",
        "data-testid=grouped-amount-input__swap-button",
        "data-testid=primary",
        "data-testid=secondary",
        "data-testid=sequence-index",
        "data-testid=tx-ref",
        "data-testid=validator-index",
      ]
    `);
  });

  it('should show the default state when adding a new event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('[data-testid=eth-deposit-event-form__advance] [data-accordion-trigger]').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    const validatorIndexInput = wrapper.find<HTMLInputElement>('[data-testid=validator-index] input');
    const txRefInput = wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input');
    const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
    const depositorInput = wrapper.find<HTMLInputElement>('[data-testid=depositor] .input-value');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');

    expect(validatorIndexInput.element.value).toBe('');
    expect(txRefInput.element.value).toBe('');
    expect(groupIdentifierInput.element.value).toBe('');
    expect(depositorInput.element.value).toBe('');
    expect(sequenceIndexInput.element.value).toBe('0');
  });

  it('should update when data adding a new event in a group', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { group: event, nextSequenceId: '10', type: 'group-add' } });

    await wrapper.find('[data-testid=eth-deposit-event-form__advance] [data-accordion-trigger]').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    const validatorIndexInput = wrapper.find<HTMLInputElement>('[data-testid=validator-index] input');
    const txRefInput = wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input');
    const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
    const depositorInput = wrapper.find<HTMLInputElement>('[data-testid=depositor] .input-value');
    const amountInput = wrapper.find<HTMLInputElement>('[data-testid=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');

    expect(validatorIndexInput.element.value).toBe(event.validatorIndex.toString());
    expect(txRefInput.element.value).toBe(event.txRef);
    expect(groupIdentifierInput.element.value).toBe(event.groupIdentifier);
    expect(depositorInput.element.value).toBe(event.locationLabel);
    expect(amountInput.element.value).toBe('0');
    expect(sequenceIndexInput.element.value).toBe('10');
  });

  it('should update the fields when editing an event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { event, nextSequenceId: '1', type: 'edit' } });

    await wrapper.find('[data-testid=eth-deposit-event-form__advance] [data-accordion-trigger]').trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    const validatorIndexInput = wrapper.find<HTMLInputElement>('[data-testid=validator-index] input');
    const txRefInput = wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input');
    const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
    const depositorInput = wrapper.find<HTMLInputElement>('[data-testid=depositor] .input-value');
    const amountInput = wrapper.find<HTMLInputElement>('[data-testid=amount] input');
    const sequenceIndexInput = wrapper.find<HTMLInputElement>('[data-testid=sequence-index] input');

    expect(validatorIndexInput.element.value).toBe(event.validatorIndex.toString());
    expect(txRefInput.element.value).toBe(event.txRef);
    expect(groupIdentifierInput.element.value).toBe(event.groupIdentifier);
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

    await wrapper.find('[data-testid=amount] input').setValue('2.5');
    await wrapper.find('[data-testid=tx-ref] input').setValue('0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef');
    await wrapper.find('[data-testid=validator-index] input').setValue('123');
    await wrapper.find('[data-testid=depositor] .input-value').setValue('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12');
    await wrapper.find('[data-testid=sequence-index] input').setValue('5');
    await wrapper.find<HTMLInputElement>('[data-testid=datetime] input').setValue(dayjs(nowInMs).format('DD/MM/YYYY HH:mm:ss.SSS'));

    const saveMethod = wrapper.vm.save;

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(addHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(addHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify('2.5'),
      depositor: '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
      entryType: HistoryEventEntryType.ETH_DEPOSIT_EVENT,
      extraData: {},
      groupIdentifier: null,
      sequenceIndex: '5',
      timestamp: nowInMs,
      txRef: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
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

    await wrapper.find('[data-testid=amount] input').setValue('4.5');
    await wrapper.find('[data-testid=validator-index] input').setValue('224');

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(editHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(editHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify('4.5'),
      depositor: event.locationLabel,
      entryType: HistoryEventEntryType.ETH_DEPOSIT_EVENT,
      extraData: {},
      groupIdentifier: event.groupIdentifier,
      identifier: event.identifier,
      sequenceIndex: event.sequenceIndex.toString(),
      timestamp: event.timestamp,
      txRef: event.txRef,
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
      message: { txRef: ['transaction hash is required'] },
      success: false,
    });

    await wrapper.find('[data-testid=validator-index] input').setValue('123123');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    const saveResult = await saveMethod();
    await nextTick();

    expect(editHistoryEventMock).toHaveBeenCalled();
    expect(saveResult).toBe(false);
    expect(wrapper.find('[data-testid=tx-ref] .details').text()).toBe('transaction hash is required');
  });

  it('should display validation errors when the form is invalid', async () => {
    wrapper = createWrapper();
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-testid=depositor] .details').exists()).toBe(true);
    expect(wrapper.find('[data-testid=validator-index] .details').exists()).toBe(true);
    expect(wrapper.find('[data-testid=tx-ref] .details').exists()).toBe(true);
  });

  describe('actualGroupIdentifier', () => {
    const eventWithActualGroupIdentifier: EthDepositEvent = {
      ...event,
      actualGroupIdentifier: 'ACTUAL123',
      groupIdentifier: 'LINKED456',
    };

    it('should use actualGroupIdentifier when present and disable the field', async () => {
      wrapper = createWrapper({
        props: { data: { event: eventWithActualGroupIdentifier, nextSequenceId: '1', type: 'edit' } },
      });
      await vi.advanceTimersToNextTimerAsync();

      await wrapper.find('[data-testid=eth-deposit-event-form__advance] [data-accordion-trigger]').trigger('click');
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

      await wrapper.find('[data-testid=eth-deposit-event-form__advance] [data-accordion-trigger]').trigger('click');
      await vi.advanceTimersToNextTimerAsync();

      const groupIdentifierInput = wrapper.find<HTMLInputElement>('[data-testid=group-identifier] input');
      expect(groupIdentifierInput.element.value).toBe(event.groupIdentifier);
      expect(groupIdentifierInput.element.disabled).toBe(false);
    });
  });
});
