import type { GroupAddEventData, GroupEventData } from '@/modules/history/management/forms/form-types';
import type { AddSolanaSwapEventPayload, EditSolanaSwapEventPayload, SolanaSwapEvent } from '@/types/history/events/schemas';
import type { TradeLocationData } from '@/types/history/trade/location';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { computed, nextTick } from 'vue';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useAddressesNamesApi } from '@/composables/api/blockchain/addresses-names';
import { useHistoryEvents } from '@/composables/history/events';
import { useLocations } from '@/composables/locations';
import SolanaSwapEventForm from '@/modules/history/management/forms/SolanaSwapEventForm.vue';
import { useMessageStore } from '@/store/message';
import { SOLANA_CHAIN } from '@/types/asset';
import { setupDayjs } from '@/utils/date';

vi.mock('@/composables/history/events', () => ({
  useHistoryEvents: vi.fn(),
}));

vi.mock('@/store/message', () => ({
  useMessageStore: vi.fn(),
}));

vi.mock('@/composables/locations', () => ({
  useLocations: vi.fn(),
}));

vi.mock('@/composables/api/assets/info', () => ({
  useAssetInfoApi: vi.fn(),
}));

vi.mock('@/composables/api/blockchain/addresses-names', () => ({
  useAddressesNamesApi: vi.fn(),
}));

describe('forms/SolanaSwapEventForm', () => {
  let addHistoryEventMock: ReturnType<typeof vi.fn>;
  let editHistoryEventMock: ReturnType<typeof vi.fn>;
  let setMessageMock: ReturnType<typeof vi.fn>;
  let fetchAddressBookMock: ReturnType<typeof vi.fn>;
  let wrapper: VueWrapper<InstanceType<typeof SolanaSwapEventForm>>;
  let pinia: Pinia;

  const signature = '5j7s6NiJS3JAkvgkoc18WpRHTZBBSz9GJPNvr1XmBEjGVaVe6RmQ6YkC6LyZNMfkZqCjhTMTDTTsF4g3XCk5jxZg';
  const address = '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU';
  const locationLabel = 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG7EvgfK';
  const eventIdentifier = `1${signature}`;

  const data: GroupEventData<SolanaSwapEvent> = {
    eventsInGroup: [{
      address,
      amount: bigNumberify('0.1'),
      asset: 'SOL',
      autoNotes: 'Swap 0.1 SOL on Jupiter',
      counterparty: 'jupiter',
      entryType: 'solana swap event',
      eventIdentifier,
      eventSubtype: 'spend',
      eventType: 'trade',
      extraData: null,
      identifier: 3456,
      location: 'solana',
      locationLabel,
      sequenceIndex: 0,
      signature,
      timestamp: 1742901211000,
      userNotes: 'spend note',
    }, {
      address: '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8',
      amount: bigNumberify('300'),
      asset: 'USDC',
      autoNotes: 'Receive 300 USDC after a swap on Jupiter',
      counterparty: 'jupiter',
      entryType: 'solana swap event',
      eventIdentifier,
      eventSubtype: 'receive',
      eventType: 'trade',
      extraData: null,
      identifier: 3457,
      location: 'solana',
      locationLabel,
      sequenceIndex: 1,
      signature,
      timestamp: 1742901211000,
      userNotes: 'receive note',
    }, {
      address: '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8',
      amount: bigNumberify('0.000005'),
      asset: 'SOL',
      autoNotes: 'Spend 0.000005 SOL as fee',
      counterparty: 'jupiter',
      entryType: 'solana swap event',
      eventIdentifier,
      eventSubtype: 'fee',
      eventType: 'trade',
      extraData: null,
      identifier: 3458,
      location: 'solana',
      locationLabel,
      sequenceIndex: 2,
      signature,
      timestamp: 1742901211000,
      userNotes: 'fee note',
    }],
    type: 'edit-group',
  };

  const groupAddData: GroupAddEventData<SolanaSwapEvent> = {
    group: data.eventsInGroup[0],
    nextSequenceId: '3',
    type: 'group-add',
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
    setMessageMock = vi.fn();
    fetchAddressBookMock = vi.fn().mockResolvedValue({
      result: [],
      success: true,
    });

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

    (useMessageStore as unknown as Mock).mockReturnValue({
      setMessage: setMessageMock,
    });

    (useAssetInfoApi as Mock).mockReturnValue({
      assetSearch: vi.fn(),
    });

    (useAddressesNamesApi as Mock).mockReturnValue({
      fetchAddressBook: fetchAddressBookMock,
    });
  });

  afterEach(() => {
    wrapper.unmount();
    vi.useRealTimers();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof SolanaSwapEventForm> = {
    props: {
      data: { nextSequenceId: '0', type: 'add' },
    },
  }): VueWrapper<InstanceType<typeof SolanaSwapEventForm>> => mount(SolanaSwapEventForm, {
    global: {
      plugins: [pinia],
    },
    ...options,
  });

  it('should render the form correctly', () => {
    wrapper = createWrapper();
    expect(wrapper.exists()).toBe(true);
    expect(wrapper.find('[data-cy=datetime]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=location]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=signature]').exists()).toBe(true);

    expect(wrapper.find('[data-cy=spend-amount]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=spend-asset]').exists()).toBe(true);

    expect(wrapper.find('[data-cy=receive-amount]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=receive-asset]').exists()).toBe(true);

    expect(wrapper.find('[data-cy=has-fee]').exists()).toBe(true);
    expect((wrapper.find('[data-cy=has-fee]').element as HTMLInputElement).checked).toBeUndefined();
    expect(wrapper.find('[data-cy=fee-amount]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=fee-asset]').exists()).toBe(true);

    expect(wrapper.find('[data-cy=address]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=sequence-index]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=counterparty]').exists()).toBe(true);

    expect(wrapper.find('[data-cy=spend-notes]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=receive-notes]').exists()).toBe(true);
    expect(wrapper.find('[data-cy=fee-notes]').exists()).toBe(true);
  });

  it('should enable fee-related fields when "Has Fee" checkbox is toggled', async () => {
    wrapper = createWrapper();

    const feeToggle = wrapper.find('[data-cy=has-fee] input');

    expect(wrapper.find('[data-cy=fee-amount] input').attributes('disabled')).toBeFalsy();
    expect(wrapper.find('[data-cy=fee-asset] input').attributes('disabled')).toBeFalsy();

    await feeToggle.setValue(true);
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-cy=fee-amount] input').attributes('disabled')).toBeFalsy();
    expect(wrapper.find('[data-cy=fee-asset] input').attributes('disabled')).toBeFalsy();
    expect(wrapper.find('[data-cy=fee-notes]').exists()).toBe(true);
  });

  it('should validate the form and call addHistoryEvent on save', async () => {
    wrapper = createWrapper({
      props: {
        data: groupAddData,
      },
    });

    await vi.advanceTimersToNextTimerAsync();

    const spendAmountField = wrapper.find('[data-cy=spend-amount] input');
    const spendAssetField = wrapper.find('[data-cy=spend-asset] input');
    const receiveAmountField = wrapper.find('[data-cy=receive-amount] input');
    const receiveAssetField = wrapper.find('[data-cy=receive-asset] input');
    const addressField = wrapper.find('[data-cy=address] input');
    const counterpartyField = wrapper.find('[data-cy=counterparty] input');

    await spendAmountField.setValue('0.1');
    await spendAssetField.setValue('SOL');
    await receiveAmountField.setValue('300');
    await receiveAssetField.setValue('USDC');
    await addressField.setValue('675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8');
    await counterpartyField.setValue('orca');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    addHistoryEventMock.mockResolvedValueOnce({ success: true });

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(addHistoryEventMock).toHaveBeenCalledTimes(1);
    expect(addHistoryEventMock).toHaveBeenCalledWith(
      expect.objectContaining({
        address: '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8',
        counterparty: 'orca',
        entryType: HistoryEventEntryType.SOLANA_SWAP_EVENT,
        receive: [{
          amount: '300',
          asset: 'USDC',
        }],
        sequenceIndex: '3',
        signature,
        spend: [{
          amount: '0.1',
          asset: 'SOL',
        }],
        timestamp: 1742901211000,
      } satisfies AddSolanaSwapEventPayload),
    );
  });

  it('should display validation errors when the form is invalid', async () => {
    wrapper = createWrapper();
    const saveMethod = wrapper.vm.save;

    await saveMethod();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-cy=signature] .details').exists()).toBe(true);
    expect(wrapper.find('[data-cy=spend-amount] .details').exists()).toBe(true);
    expect(wrapper.find('[data-cy=spend-asset] .details').exists()).toBe(true);
    expect(wrapper.find('[data-cy=receive-amount] .details').exists()).toBe(true);
    expect(wrapper.find('[data-cy=receive-asset] .details').exists()).toBe(true);
  });

  it('calls editHistoryEvent when editing an event', async () => {
    wrapper = createWrapper({
      props: {
        data,
      },
    });

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoryEventMock.mockResolvedValueOnce({ success: false });

    let saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(editHistoryEventMock).not.toHaveBeenCalled();

    const feeAmount = wrapper.find('[data-cy=fee-amount] input');
    await feeAmount.setValue('0.00001');

    const receiveNotes = wrapper.find('[data-cy=receive-notes] textarea:not([aria-hidden="true"])');
    const feeNotes = wrapper.find('[data-cy=fee-notes] textarea:not([aria-hidden="true"])');
    await receiveNotes.setValue('updated receive note');
    await feeNotes.setValue('updated fee note');

    await vi.advanceTimersToNextTimerAsync();

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoryEventMock.mockResolvedValueOnce({ success: false });

    saveResult = await saveMethod();
    expect(saveResult).toBe(true);

    expect(editHistoryEventMock).toHaveBeenCalledWith(
      expect.objectContaining({
        address,
        counterparty: 'jupiter',
        entryType: 'solana swap event',
        fee: [{
          amount: '0.00001',
          asset: 'SOL',
          identifier: 3458,
          locationLabel,
          userNotes: 'updated fee note',
        }],
        identifiers: [3456, 3457, 3458],
        receive: [{
          amount: '300',
          asset: 'USDC',
          identifier: 3457,
          locationLabel,
          userNotes: 'updated receive note',
        }],
        sequenceIndex: '0',
        signature,
        spend: [{
          amount: '0.1',
          asset: 'SOL',
          identifier: 3456,
          locationLabel,
          userNotes: 'spend note',
        }],
        timestamp: 1742901211000,
      } satisfies EditSolanaSwapEventPayload),
    );
    expect(addHistoryEventMock).toHaveBeenCalledTimes(0);
  });

  it('should add extra values to make a swap multi-swap', async () => {
    wrapper = createWrapper({
      props: {
        data,
      },
    });

    await vi.advanceTimersToNextTimerAsync();

    const feeAmount = wrapper.find('[data-cy=fee-amount] input');
    await feeAmount.setValue('0.00001');

    const receiveNotes = wrapper.find('[data-cy=receive-notes] textarea:not([aria-hidden="true"])');
    const feeNotes = wrapper.find('[data-cy=fee-notes] textarea:not([aria-hidden="true"])');
    await receiveNotes.setValue('updated receive note');
    await feeNotes.setValue('updated fee note');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoryEventMock.mockResolvedValueOnce({ success: false });

    await wrapper.find('[data-cy=spend-add]').trigger('click');
    await wrapper.find('[data-cy=receive-add]').trigger('click');

    await wrapper.findAll('[data-cy=spend-amount] input')[1].setValue('0.2');
    await wrapper.findAll('[data-cy=spend-asset] input')[1].setValue('RAY');

    await wrapper.findAll('[data-cy=receive-amount] input')[1].setValue('0.19');
    await wrapper.findAll('[data-cy=receive-asset] input')[1].setValue('USDC');

    await wrapper.find('[data-cy=spend-add]').trigger('click');
    expect(wrapper.findAll('[data-cy=spend-amount]')).toHaveLength(3);
    await wrapper.findAll('[data-cy=spend-remove]')[2].trigger('click');
    expect(wrapper.findAll('[data-cy=spend-amount]')).toHaveLength(2);

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(editHistoryEventMock).toHaveBeenCalledWith(
      expect.objectContaining({
        address,
        counterparty: 'jupiter',
        entryType: 'solana swap event',
        fee: [{
          amount: '0.00001',
          asset: 'SOL',
          identifier: 3458,
          locationLabel,
          userNotes: 'updated fee note',
        }],
        identifiers: [3456, 3457, 3458],
        receive: [{
          amount: '300',
          asset: 'USDC',
          identifier: 3457,
          locationLabel,
          userNotes: 'updated receive note',
        }, {
          amount: '0.19',
          asset: 'USDC',
        }],
        sequenceIndex: '0',
        signature,
        spend: [{
          amount: '0.1',
          asset: 'SOL',
          identifier: 3456,
          locationLabel,
          userNotes: 'spend note',
        }, {
          amount: '0.2',
          asset: 'RAY',
        }],
        timestamp: 1742901211000,
      } satisfies EditSolanaSwapEventPayload),
    );
    expect(addHistoryEventMock).toHaveBeenCalledTimes(0);
  });

  it('should remove the fee', async () => {
    wrapper = createWrapper({
      props: {
        data,
      },
    });

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    editHistoryEventMock.mockResolvedValueOnce({ success: true });
    addHistoryEventMock.mockResolvedValueOnce({ success: false });

    await wrapper.find('[data-cy=has-fee] input').setValue(false);

    const saveResult = await saveMethod();
    expect(saveResult).toBe(true);
    expect(editHistoryEventMock).toHaveBeenCalledWith(
      expect.objectContaining({
        address,
        counterparty: 'jupiter',
        entryType: 'solana swap event',
        identifiers: [3456, 3457, 3458],
        receive: [{
          amount: '300',
          asset: 'USDC',
          identifier: 3457,
          locationLabel,
          userNotes: 'receive note',
        }],
        sequenceIndex: '0',
        signature,
        spend: [{
          amount: '0.1',
          asset: 'SOL',
          identifier: 3456,
          locationLabel,
          userNotes: 'spend note',
        }],
        timestamp: 1742901211000,
      } satisfies EditSolanaSwapEventPayload),
    );
    expect(addHistoryEventMock).toHaveBeenCalledTimes(0);
  });

  it('should handle server validation errors', async () => {
    wrapper = createWrapper({
      props: {
        data,
      },
    });

    editHistoryEventMock.mockResolvedValueOnce({
      message: { address: ['Invalid Solana address format'] },
      success: false,
    });

    await wrapper.find('[data-cy=address] input').setValue('DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG7EvgfK');

    await vi.advanceTimersToNextTimerAsync();

    const saveMethod = wrapper.vm.save;

    const saveResult = await saveMethod();
    await nextTick();

    expect(editHistoryEventMock).toHaveBeenCalled();
    expect(saveResult).toBe(false);
    expect(wrapper.find('[data-cy=address] .details').text()).toBe('Invalid Solana address format');
  });

  it('should load data correctly for group-add mode', async () => {
    wrapper = createWrapper({
      props: {
        data: groupAddData,
      },
    });

    await vi.advanceTimersToNextTimerAsync();

    const signatureField = wrapper.find<HTMLInputElement>('[data-cy=signature] input');
    expect(signatureField.element.value).toBe(signature);

    const locationField = wrapper.find<HTMLInputElement>('[data-cy=location] input');
    expect(locationField.element.value).toBe(SOLANA_CHAIN);

    const sequenceIndexField = wrapper.find<HTMLInputElement>('[data-cy=sequence-index] input');
    expect(sequenceIndexField.element.value).toBe('3');
  });
});
