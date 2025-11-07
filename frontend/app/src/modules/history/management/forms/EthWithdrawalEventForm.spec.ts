import type { AssetMap } from '@/types/asset';
import type { EthWithdrawalEvent } from '@/types/history/events/schemas';
import { bigNumberify, HistoryEventEntryType, One } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { nextTick } from 'vue';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { useHistoryEvents } from '@/composables/history/events';
import EthWithdrawalEventForm from '@/modules/history/management/forms/EthWithdrawalEventForm.vue';
import { useBalancePricesStore } from '@/store/balances/prices';
import { setupDayjs } from '@/utils/date';

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn(),
}));

vi.mock('@/composables/api/assets/info', () => ({
  useAssetInfoApi: vi.fn(),
}));

vi.mock('@/composables/history/events', () => ({
  useHistoryEvents: vi.fn(),
}));

vi.mock('@/composables/api/assets/prices', () => ({
  useAssetPricesApi: vi.fn().mockReturnValue({
    addHistoricalPrice: vi.fn(),
  }),
}));

describe('forms/EthWithdrawalEventForm.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof EthWithdrawalEventForm>>;
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

  const event: EthWithdrawalEvent = {
    amount: bigNumberify('2.5'),
    asset: asset.symbol,
    entryType: HistoryEventEntryType.ETH_WITHDRAWAL_EVENT,
    eventSubtype: 'remove asset',
    eventType: 'staking',
    groupIdentifier: 'EW_123_19647',
    identifier: 11343,
    isExit: true,
    location: 'ethereum',
    locationLabel: '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    sequenceIndex: 0,
    timestamp: 1697517629000,
    userNotes: 'Exit validator 123 with 2.5 ETH',
    validatorIndex: 123,
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
    const assetMapping = vi.fn().mockResolvedValue(mapping);
    (useBalancePricesStore as unknown as Mock).mockReturnValue({
      getHistoricPrice: vi.fn().mockResolvedValue(One),
    });
    (useAssetInfoApi as Mock).mockReturnValue({ assetMapping });
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

  const createWrapper = (options: ComponentMountingOptions<typeof EthWithdrawalEventForm> = {
    props: {
      data: { nextSequenceId: '0', type: 'add' },
    },
  }): VueWrapper<InstanceType<typeof EthWithdrawalEventForm>> => mount(EthWithdrawalEventForm, {
    global: {
      plugins: [pinia],
    },
    ...options,
  });

  it('should show the default state when adding a new event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const validatorIndexInput = wrapper.find<HTMLInputElement>('[data-cy=validatorIndex] input');
    const withdrawalAddressInput = wrapper.find<HTMLInputElement>('[data-cy=withdrawalAddress] .input-value');
    const isExitCheckbox = wrapper.find<HTMLInputElement>('[data-cy=is-exit] input');

    expect(validatorIndexInput.element.value).toBe('');
    expect(withdrawalAddressInput.element.value).toBe('');
    expect(isExitCheckbox.element.checked).toBeFalsy();
  });

  it('should update the fields when adding an event in an existing group', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { group: event, nextSequenceId: '1', type: 'group-add' } });

    const validatorIndexInput = wrapper.find<HTMLInputElement>('[data-cy=validatorIndex] input');
    const withdrawalAddressInput = wrapper.find<HTMLInputElement>('[data-cy=withdrawalAddress] .input-value');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const isExitedCheckbox = wrapper.find<HTMLInputElement>('[data-cy=is-exit] input');

    expect(validatorIndexInput.element.value).toBe(event.validatorIndex.toString());
    expect(withdrawalAddressInput.element.value).toBe(event.locationLabel);
    expect(amountInput.element.value).toBe('0');
    expect(isExitedCheckbox.element.checked).toBeFalsy();
  });

  it('it should update the fields when editing an event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { event, nextSequenceId: '1', type: 'edit' } });

    const validatorIndexInput = wrapper.find<HTMLInputElement>('[data-cy=validatorIndex] input');
    const withdrawalAddressInput = wrapper.find<HTMLInputElement>('[data-cy=withdrawalAddress] .input-value');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const isExitedCheckbox = wrapper.find<HTMLInputElement>('[data-cy=is-exit] input');

    expect(validatorIndexInput.element.value).toBe(event.validatorIndex.toString());
    expect(withdrawalAddressInput.element.value).toBe(event.locationLabel);
    expect(amountInput.element.value).toBe(event.amount.toString());
    expect(isExitedCheckbox.element.checked).toBeTruthy();
  });

  it('should add a new withdrawal event when form is submitted', async () => {
    wrapper = createWrapper();
    await nextTick();
    await vi.advanceTimersToNextTimerAsync();

    const now = dayjs();
    const nowInMs = now.valueOf();

    await wrapper.find('[data-cy=amount] input').setValue('2.5');
    await wrapper.find('[data-cy=validatorIndex] input').setValue('123');
    await wrapper.find('[data-cy=withdrawalAddress] .input-value').setValue('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12');
    await wrapper.find<HTMLInputElement>('[data-cy=datetime] input').setValue(dayjs(nowInMs).format('DD/MM/YYYY HH:mm:ss.SSS'));
    await wrapper.find('[data-cy=is-exit] input').setValue(true);

    const saveMethod = wrapper.vm.save;

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(addHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(addHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify('2.5'),
      entryType: HistoryEventEntryType.ETH_WITHDRAWAL_EVENT,
      groupIdentifier: null,
      isExit: true,
      timestamp: nowInMs,
      validatorIndex: 123,
      withdrawalAddress: '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
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
    await wrapper.find('[data-cy=is-exit] input').setValue(false);

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(editHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(editHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify('4.5'),
      entryType: HistoryEventEntryType.ETH_WITHDRAWAL_EVENT,
      groupIdentifier: event.groupIdentifier,
      identifier: event.identifier,
      isExit: false,
      timestamp: event.timestamp,
      validatorIndex: 224,
      withdrawalAddress: '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
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
      message: { withdrawalAddress: ['withdrawal address is required'] },
      success: false,
    });

    await wrapper.find('[data-cy=amount] input').setValue('4.5');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    const saveResult = await saveMethod();
    await nextTick();

    expect(editHistoryEventMock).toHaveBeenCalled();
    expect(saveResult).toBe(false);
    expect(wrapper.find('[data-cy=withdrawalAddress] .details').text()).toBe('withdrawal address is required');
  });

  it('should display validation errors when the form is invalid', async () => {
    wrapper = createWrapper();
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-cy=withdrawalAddress] .details').exists()).toBe(true);
    expect(wrapper.find('[data-cy=validatorIndex] .details').exists()).toBe(true);
  });
});
