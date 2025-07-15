import type { AssetMap } from '@/types/asset';
import type { EthBlockEvent } from '@/types/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import dayjs from 'dayjs';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { nextTick } from 'vue';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { useHistoryEvents } from '@/composables/history/events';
import EthBlockEventForm from '@/modules/history/management/forms/EthBlockEventForm.vue';
import { setupDayjs } from '@/utils/date';

vi.mock('@/composables/history/events', () => ({
  useHistoryEvents: vi.fn(),
}));

vi.mock('@/composables/api/assets/prices', () => ({
  useAssetPricesApi: vi.fn().mockReturnValue({
    addHistoricalPrice: vi.fn(),
  }),
}));

describe('forms/EthBlockEventForm.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof EthBlockEventForm>>;
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

  const event: EthBlockEvent = {
    amount: bigNumberify('100'),
    asset: asset.symbol,
    blockNumber: 444,
    entryType: HistoryEventEntryType.ETH_BLOCK_EVENT,
    eventIdentifier: 'BP1_444',
    eventSubtype: 'mev reward',
    eventType: 'staking',
    identifier: 11336,
    location: 'ethereum',
    locationLabel: '0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa',
    sequenceIndex: 0,
    timestamp: 1697442021000,
    userNotes:
      'Validator 12 produced block 444 with 100 ETH going to 0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa as the mev reward',
    validatorIndex: 122,
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

  const createWrapper = (options: ComponentMountingOptions<typeof EthBlockEventForm> = {
    props: {
      data: { nextSequenceId: '0', type: 'add' },
    },
  }): VueWrapper<InstanceType<typeof EthBlockEventForm>> =>
    mount(EthBlockEventForm, {
      global: {
        plugins: [pinia],
      },
      ...options,
    });

  it('should show the default state when adding a new event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const blockNumberInput = wrapper.find<HTMLInputElement>('[data-cy=blockNumber] input');
    const validatorIndexInput = wrapper.find<HTMLInputElement>('[data-cy=validatorIndex] input');
    const feeRecipientInput = wrapper.find<HTMLInputElement>('[data-cy=feeRecipient] .input-value');
    const mevRewardCheckbox = wrapper.find<HTMLInputElement>('[data-cy=isMevReward] input');

    expect(blockNumberInput.element.value).toBe('');
    expect(validatorIndexInput.element.value).toBe('');
    expect(feeRecipientInput.element.value).toBe('');
    expect(mevRewardCheckbox.element.checked).toBeFalsy();
  });

  it('should update the relevant fields when adding an event to a group', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { group: event, nextSequenceId: '1', type: 'group-add' } });

    const blockNumberInput = wrapper.find<HTMLInputElement>('[data-cy=blockNumber] input');
    const validatorIndexInput = wrapper.find<HTMLInputElement>('[data-cy=validatorIndex] input');
    const feeRecipientInput = wrapper.find<HTMLInputElement>('[data-cy=feeRecipient] .input-value');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const isMevCheckbox = wrapper.find<HTMLInputElement>('[data-cy=isMevReward] input');

    expect(blockNumberInput.element.value).toBe(event.blockNumber.toString());
    expect(validatorIndexInput.element.value).toBe(event.validatorIndex.toString());
    expect(feeRecipientInput.element.value).toBe(event.locationLabel);
    expect(amountInput.element.value).toBe('0');
    expect(isMevCheckbox.element.checked).toBeFalsy();
  });

  it('should update the fields when editing an event', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.setProps({ data: { event, nextSequenceId: '1', type: 'edit' } });

    const blockNumberInput = wrapper.find<HTMLInputElement>('[data-cy=blockNumber] input');
    const validatorIndexInput = wrapper.find<HTMLInputElement>('[data-cy=validatorIndex] input');
    const feeRecipientInput = wrapper.find<HTMLInputElement>('[data-cy=feeRecipient] .input-value');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const isMevCheckbox = wrapper.find<HTMLInputElement>('[data-cy=isMevReward] input');

    expect(blockNumberInput.element.value).toBe(event.blockNumber.toString());
    expect(validatorIndexInput.element.value).toBe(event.validatorIndex.toString());
    expect(feeRecipientInput.element.value).toBe(event.locationLabel);
    expect(amountInput.element.value).toBe(event.amount.toString());
    expect(isMevCheckbox.element.checked).toBeTruthy();
  });

  it('should call addHistoryEvent when adding a new block event on save', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    const now = dayjs();
    const nowInMs = now.valueOf();

    const blockNumberInput = wrapper.find<HTMLInputElement>('[data-cy=blockNumber] input');
    const validatorIndexInput = wrapper.find<HTMLInputElement>('[data-cy=validatorIndex] input');
    const feeRecipientInput = wrapper.find<HTMLInputElement>('[data-cy=feeRecipient] .input-value');
    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    const isMevCheckbox = wrapper.find<HTMLInputElement>('[data-cy=isMevReward] input');
    const dateInput = wrapper.find<HTMLInputElement>('[data-cy=datetime] input');

    await blockNumberInput.setValue(event.blockNumber);
    await validatorIndexInput.setValue(event.validatorIndex);
    await feeRecipientInput.setValue(event.locationLabel);
    await amountInput.setValue('50');
    await isMevCheckbox.setValue(event.eventSubtype === 'mev reward');
    await dateInput.setValue(dayjs(nowInMs).format('DD/MM/YYYY HH:mm:ss.SSS'));

    const saveMethod = wrapper.vm.save;

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(addHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(addHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify('50'),
      blockNumber: event.blockNumber,
      entryType: HistoryEventEntryType.ETH_BLOCK_EVENT,
      eventIdentifier: null,
      feeRecipient: event.locationLabel,
      isMevReward: event.eventSubtype === 'mev reward',
      timestamp: nowInMs,
      validatorIndex: event.validatorIndex,
    });
  });

  it('should not call editHistoryEvent when only updating the historic price', async () => {
    wrapper = createWrapper({
      props: { data: { event, nextSequenceId: '1', type: 'edit' } },
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

  it('should call editHistoryEvent when editing a block event on save', async () => {
    wrapper = createWrapper({
      props: { data: { event, nextSequenceId: '1', type: 'edit' } },
    });
    await vi.advanceTimersToNextTimerAsync();

    const amountInput = wrapper.find<HTMLInputElement>('[data-cy=amount] input');
    await amountInput.setValue('52');

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(editHistoryEventMock).toHaveBeenCalledTimes(1);

    expect(editHistoryEventMock).toHaveBeenCalledWith({
      amount: bigNumberify('52'),
      blockNumber: event.blockNumber,
      entryType: HistoryEventEntryType.ETH_BLOCK_EVENT,
      eventIdentifier: event.eventIdentifier,
      feeRecipient: event.locationLabel,
      identifier: event.identifier,
      isMevReward: event.eventSubtype === 'mev reward',
      timestamp: event.timestamp,
      validatorIndex: event.validatorIndex,
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
      message: { timestamp: ['invalid date passed'] },
      success: false,
    });

    await wrapper.find('[data-cy=blockNumber] input').setValue('111');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    const saveResult = await saveMethod();
    await nextTick();

    expect(editHistoryEventMock).toHaveBeenCalled();
    expect(saveResult).toBe(false);
    expect(wrapper.find('[data-cy=datetime] .details').text()).toBe('invalid date passed');
  });

  it('should display validation errors when the form is invalid', async () => {
    wrapper = createWrapper();
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-cy=blockNumber] .details').exists()).toBe(true);
    expect(wrapper.find('[data-cy=validatorIndex] .details').exists()).toBe(true);
  });
});
