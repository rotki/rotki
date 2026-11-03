import type { Pinia } from 'pinia';
import type { TradeLocationData } from '@/modules/core/common/location';
import type { EvmSwapEvent, SolanaSwapEvent, SwapEvent } from '@/modules/history/events/schemas';
import type { GroupEventData } from '@/modules/history/management/forms/form-types';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { selectorContract } from '@test/utils/selector-contract';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { useAddressesNamesApi } from '@/modules/accounts/address-book/use-addresses-names-api';
import { useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { SOLANA_CHAIN } from '@/modules/assets/types';
import { setupDayjs } from '@/modules/core/common/data/date';
import { useLocations } from '@/modules/core/common/use-locations';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';
import SwapEventForm from '@/modules/history/management/forms/SwapEventForm.vue';

vi.mock('@/modules/history/events/use-history-events', () => ({
  useHistoryEvents: vi.fn(),
}));

vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: vi.fn(),
}));

/** The locations an evm swap can be on, which decide the kind of a swap being added. */
const evmLocations = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return ref<string[]>([]);
});

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { mockUseSupportedChains } = await import('@test/utils/mocks/supported-chains');
  const vue = await import('vue');
  return mockUseSupportedChains({ txChainsToLocation: vue.computed<string[]>(() => vue.toValue(evmLocations)) });
});

vi.mock('@/modules/assets/api/use-asset-info-api', () => ({
  useAssetInfoApi: vi.fn(),
}));

vi.mock('@/modules/accounts/address-book/use-addresses-names-api', () => ({
  useAddressesNamesApi: vi.fn(),
}));

/** The options the form hands the transaction lookup, so a test can ask when it would run, and how often it was reset. */
const lookup = vi.hoisted(() => ({ enabled: (): boolean => false, resets: 0 }));

vi.mock('@/modules/history/management/forms/use-evm-tx-lookup', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/modules/history/management/forms/use-evm-tx-lookup')>();
  return {
    ...original,
    useEvmTxAutoFill: (options: Parameters<typeof original.useEvmTxAutoFill>[0]): ReturnType<typeof original.useEvmTxAutoFill> => {
      lookup.enabled = (): boolean => toValue(options.enabled);
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

type HistoryEvents = ReturnType<typeof useHistoryEvents>;

type Wrapper = VueWrapper<InstanceType<typeof SwapEventForm>>;

type SwapGroupData = GroupEventData<SwapEvent | EvmSwapEvent | SolanaSwapEvent>;

const TIMESTAMP = 1742901211000;
const evmTxRef = '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f';
const evmAddress = '0xA090e606E30bD747d4E6245a1517EbE430F0057e';
const evmAccount = '0x6e15887E2CEC81434C16D587709f64603b39b541';
const solanaTxRef = '5wHu1qwD4kLwYqCEuNqTvhpFvGYRVYVEHVsdvR2v3Wg7fFyGxUWJTgL4wZ3Y1sM9RcYnPbLXZhKUqLNvV7kA8dQz';

const addData: SwapGroupData = { nextSequenceId: '0', type: 'add' };

function plainEvent(subtype: string, identifier: number, amount: string, asset: string): SwapEvent {
  return {
    amount: bigNumberify(amount),
    asset,
    autoNotes: '',
    entryType: HistoryEventEntryType.SWAP_EVENT,
    eventSubtype: subtype,
    eventType: 'trade',
    extraData: null,
    groupIdentifier: 'group',
    identifier,
    location: 'kraken',
    locationLabel: null,
    sequenceIndex: 0,
    timestamp: TIMESTAMP,
    userNotes: `${subtype} note`,
  };
}

function evmEvent(subtype: string, identifier: number, amount: string, asset: string): EvmSwapEvent {
  return {
    address: evmAddress,
    amount: bigNumberify(amount),
    asset,
    autoNotes: '',
    counterparty: 'uniswap-v3',
    entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
    eventSubtype: subtype,
    eventType: 'trade',
    extraData: null,
    groupIdentifier: `1${evmTxRef}`,
    identifier,
    location: 'ethereum',
    locationLabel: evmAccount,
    sequenceIndex: 0,
    timestamp: TIMESTAMP,
    txRef: evmTxRef,
    userNotes: '',
  };
}

describe('forms/SwapEventForm', () => {
  let addHistoryEvent: ReturnType<typeof vi.fn<HistoryEvents['addHistoryEvent']>>;
  let editHistoryEvent: ReturnType<typeof vi.fn<HistoryEvents['editHistoryEvent']>>;
  let wrapper: Wrapper;
  let pinia: Pinia;

  beforeAll(() => {
    setupDayjs();
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    vi.useFakeTimers();
    set(evmLocations, ['ethereum', 'optimism']);
    addHistoryEvent = vi.fn<HistoryEvents['addHistoryEvent']>().mockResolvedValue({ success: true });
    editHistoryEvent = vi.fn<HistoryEvents['editHistoryEvent']>().mockResolvedValue({ success: true });

    vi.mocked(useLocations).mockReturnValue(createMock<ReturnType<typeof useLocations>>({
      tradeLocations: computed<TradeLocationData[]>(() => [{ identifier: 'kraken', name: 'Kraken' }]),
    }));
    vi.mocked(useHistoryEvents).mockReturnValue(createMock<HistoryEvents>({ addHistoryEvent, editHistoryEvent }));
    vi.mocked(useAssetInfoApi).mockReturnValue(createMock<ReturnType<typeof useAssetInfoApi>>());
    vi.mocked(useAddressesNamesApi).mockReturnValue(createMock<ReturnType<typeof useAddressesNamesApi>>({
      fetchAddressBook: vi.fn<ReturnType<typeof useAddressesNamesApi>['fetchAddressBook']>()
        .mockResolvedValue({ data: [], found: 0, limit: -1, total: 0 }),
    }));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  async function locate(location: string): Promise<void> {
    await wrapper.findComponent({ name: 'LocationSelector' }).setValue(location);
  }

  async function createWrapper(data: SwapGroupData = addData): Promise<Wrapper> {
    wrapper = mount(SwapEventForm, {
      global: { plugins: [pinia] },
      props: { data },
    });
    await vi.advanceTimersToNextTimerAsync();
    return wrapper;
  }

  async function fill(testid: string, value: string): Promise<void> {
    await wrapper.find(`[data-testid=${testid}] input`).setValue(value);
  }

  async function fillRows(): Promise<void> {
    await wrapper.find('[data-testid=sub-event-amount][data-key=spend] input').setValue('0.1');
    await wrapper.find('[data-testid=sub-event-asset][data-key=spend] input').setValue('ETH');
    await wrapper.find('[data-testid=sub-event-amount][data-key=receive] input').setValue('300');
    await wrapper.find('[data-testid=sub-event-asset][data-key=receive] input').setValue('USDC');
  }

  function has(selector: string): boolean {
    return wrapper.find(selector).exists();
  }

  describe('the selectors the e2e suite uses', () => {
    it('should keep them for an evm swap', async () => {
      await createWrapper();
      await locate('ethereum');

      expect(selectorContract(wrapper)).toMatchInlineSnapshot(`
        [
          "data-testid=address",
          "data-testid=advanced-accordion",
          "data-testid=counterparty",
          "data-testid=datetime",
          "data-testid=has-fee",
          "data-testid=location",
          "data-testid=location-label",
          "data-testid=receive",
          "data-testid=sequence-index",
          "data-testid=spend",
          "data-testid=sub-event-amount[data-key=receive]",
          "data-testid=sub-event-amount[data-key=spend]",
          "data-testid=sub-event-asset[data-key=receive]",
          "data-testid=sub-event-asset[data-key=spend]",
          "data-testid=swap-event-form-advance",
          "data-testid=swap-sub-event-add[data-key=receive]",
          "data-testid=swap-sub-event-add[data-key=spend]",
          "data-testid=swap-sub-event-notes[data-key=receive]",
          "data-testid=swap-sub-event-notes[data-key=spend]",
          "data-testid=tx-ref",
        ]
      `);
    });

    it('should keep them for a solana swap', async () => {
      await createWrapper();
      await locate(SOLANA_CHAIN);

      expect(selectorContract(wrapper)).toMatchInlineSnapshot(`
        [
          "data-testid=address",
          "data-testid=advanced-accordion",
          "data-testid=counterparty",
          "data-testid=datetime",
          "data-testid=has-fee",
          "data-testid=location",
          "data-testid=location-label",
          "data-testid=receive",
          "data-testid=sequence-index",
          "data-testid=spend",
          "data-testid=sub-event-amount[data-key=receive]",
          "data-testid=sub-event-amount[data-key=spend]",
          "data-testid=sub-event-asset[data-key=receive]",
          "data-testid=sub-event-asset[data-key=spend]",
          "data-testid=swap-event-form-advance",
          "data-testid=swap-sub-event-add[data-key=receive]",
          "data-testid=swap-sub-event-add[data-key=spend]",
          "data-testid=swap-sub-event-notes[data-key=receive]",
          "data-testid=swap-sub-event-notes[data-key=spend]",
          "data-testid=tx-ref",
        ]
      `);
    });

    it('should keep them for a plain swap', async () => {
      await createWrapper();

      expect(selectorContract(wrapper)).toMatchInlineSnapshot(`
        [
          "data-testid=advanced-accordion",
          "data-testid=datetime",
          "data-testid=has-fee",
          "data-testid=location",
          "data-testid=receive",
          "data-testid=spend",
          "data-testid=sub-event-amount[data-key=receive]",
          "data-testid=sub-event-amount[data-key=spend]",
          "data-testid=sub-event-asset[data-key=receive]",
          "data-testid=sub-event-asset[data-key=spend]",
          "data-testid=swap-sub-event-notes[data-key=receive]",
          "data-testid=swap-sub-event-notes[data-key=spend]",
          "data-testid=unique-id",
        ]
      `);
    });
  });

  describe('a plain swap', () => {
    it('should hold one row a side and no account, and show a unique id instead of a transaction', async () => {
      await createWrapper();

      expect(has('[data-testid=swap-sub-event-add]')).toBe(false);
      expect(has('[data-testid=location-label]')).toBe(false);
      expect(has('[data-testid=unique-id]')).toBe(true);
      expect(has('[data-testid=tx-ref]')).toBe(false);
      expect(has('[data-testid=counterparty]')).toBe(false);
    });

    it('should save the flat plain payload', async () => {
      await createWrapper();
      await fill('location', 'kraken');
      await fillRows();
      await fill('unique-id', 'abcd');

      await expect(wrapper.vm.save()).resolves.toBe(true);

      expect(addHistoryEvent).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
        entryType: HistoryEventEntryType.SWAP_EVENT,
        location: 'kraken',
        receiveAmount: '300',
        receiveAsset: 'USDC',
        spendAmount: '0.1',
        spendAsset: 'ETH',
        uniqueId: 'abcd',
        userNotes: ['', ''],
      }));
    });

    it('should send an edit with the identifiers as spend, receive, then the fees, in the group it was loaded from', async () => {
      await createWrapper({
        eventsInGroup: [plainEvent('fee', 12, '1', 'USD'), plainEvent('receive', 11, '20', 'USD'), plainEvent('spend', 10, '0.01', 'ETH')],
        type: 'edit-group',
      });
      await wrapper.find('[data-testid=sub-event-amount][data-key=spend] input').setValue('0.02');

      await expect(wrapper.vm.save()).resolves.toBe(true);

      expect(editHistoryEvent).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
        groupIdentifier: 'group',
        identifiers: [10, 11, 12],
        spendAmount: '0.02',
        uniqueId: '',
      }));
    });

    it('should show the endpoint\'s flat field errors on the rows', async () => {
      editHistoryEvent.mockResolvedValue({ message: { spendAmount: ['too small'] }, success: false });
      await createWrapper({
        eventsInGroup: [plainEvent('receive', 11, '20', 'USD'), plainEvent('spend', 10, '0.01', 'ETH')],
        type: 'edit-group',
      });
      await wrapper.find('[data-testid=sub-event-amount][data-key=spend] input').setValue('0.02');

      await expect(wrapper.vm.save()).resolves.toBe(false);
      await nextTick();

      expect(wrapper.find('[data-testid=sub-event-amount][data-key=spend] .details').text()).toBe('too small');
    });
  });

  describe('half a swap', () => {
    const halfSwap: SwapGroupData = { eventsInGroup: [evmEvent('spend', 1, '0.1', 'ETH')], type: 'edit-group' };

    it('should show that only part of the swap was loaded instead of the fields, and refuse to save it', async () => {
      await createWrapper(halfSwap);

      expect(wrapper.find('[data-testid=swap-event-form-incomplete]').text()).toBe('swap_event_form.incomplete');
      expect(has('[data-testid=location]')).toBe(false);
      await expect(wrapper.vm.save()).resolves.toBe(false);
      expect(editHistoryEvent).not.toHaveBeenCalled();
    });

    it('should not save the swap it showed before when it is pointed at half a swap', async () => {
      await createWrapper({
        eventsInGroup: [evmEvent('spend', 1, '0.1', 'ETH'), evmEvent('receive', 2, '300', 'USDC')],
        type: 'edit-group',
      });
      await wrapper.find('[data-testid=sub-event-amount][data-key=spend] input').setValue('0.2');

      await wrapper.setProps({ data: halfSwap });
      await vi.advanceTimersToNextTimerAsync();

      await expect(wrapper.vm.save()).resolves.toBe(false);
      expect(editHistoryEvent).not.toHaveBeenCalled();
    });

    it('should edit the next complete swap it is pointed at', async () => {
      await createWrapper(halfSwap);

      await wrapper.setProps({ data: {
        eventsInGroup: [evmEvent('spend', 1, '0.1', 'ETH'), evmEvent('receive', 2, '300', 'USDC')],
        type: 'edit-group',
      } });
      await vi.advanceTimersToNextTimerAsync();
      await wrapper.find('[data-testid=sub-event-amount][data-key=spend] input').setValue('0.2');

      expect(has('[data-testid=swap-event-form-incomplete]')).toBe(false);
      await expect(wrapper.vm.save()).resolves.toBe(true);
      expect(editHistoryEvent).toHaveBeenCalledOnce();
    });
  });

  describe('a chain swap', () => {
    it('should send an edit with the group\'s identifiers in the group\'s own order', async () => {
      await createWrapper({
        eventsInGroup: [evmEvent('fee', 3, '0.005', 'ETH'), evmEvent('receive', 2, '300', 'USDC'), evmEvent('spend', 1, '0.1', 'ETH')],
        type: 'edit-group',
      });
      await wrapper.find('[data-testid=sub-event-amount][data-key=spend] input').setValue('0.2');

      await expect(wrapper.vm.save()).resolves.toBe(true);

      expect(editHistoryEvent).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
        entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
        identifiers: [3, 2, 1],
        txRef: evmTxRef,
      }));
    });

    it('should keep an edited swap the kind it was saved as, on a location that would imply another', async () => {
      await createWrapper({
        eventsInGroup: [evmEvent('spend', 1, '0.1', 'ETH'), evmEvent('receive', 2, '300', 'USDC')],
        type: 'edit-group',
      });
      await wrapper.setProps({ data: {
        eventsInGroup: [{ ...evmEvent('spend', 1, '0.1', 'ETH'), location: 'base' }, { ...evmEvent('receive', 2, '300', 'USDC'), location: 'base' }],
        type: 'edit-group',
      } });
      await vi.advanceTimersToNextTimerAsync();
      await wrapper.find('[data-testid=sub-event-amount][data-key=spend] input').setValue('0.2');

      await expect(wrapper.vm.save()).resolves.toBe(true);
      expect(editHistoryEvent.mock.calls[0][0]).toMatchObject({ entryType: HistoryEventEntryType.EVM_SWAP_EVENT, location: 'base' });
    });

    it('should seed an addition into an existing transaction from that transaction', async () => {
      await createWrapper({
        group: evmEvent('spend', 1, '0.1', 'ETH'),
        nextSequenceId: '7',
        type: 'group-add',
      });
      await fillRows();

      await expect(wrapper.vm.save()).resolves.toBe(true);

      expect(addHistoryEvent).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
        location: 'ethereum',
        sequenceIndex: '7',
        timestamp: TIMESTAMP,
        txRef: evmTxRef,
      }));
    });

    it('should show the fixed solana location, locked, adding into a solana transaction', async () => {
      await createWrapper({
        group: createMock<SolanaSwapEvent>({ entryType: HistoryEventEntryType.SOLANA_SWAP_EVENT, location: 'kraken', timestamp: TIMESTAMP, txRef: solanaTxRef }),
        nextSequenceId: '3',
        type: 'group-add',
      });

      const location = wrapper.find<HTMLInputElement>('[data-testid=location] input');
      expect(location.element.disabled).toBe(true);
      expect(wrapper.findComponent({ name: 'LocationSelector' }).props('modelValue')).toBe(SOLANA_CHAIN);
    });
  });

  describe('the kind of a swap being added', () => {
    it('should start as a plain swap, with the location open', async () => {
      await createWrapper();

      expect(has('[data-testid=unique-id]')).toBe(true);
      expect(wrapper.find<HTMLInputElement>('[data-testid=location] input').element.disabled).toBe(false);
    });

    it.each([
      { location: 'optimism', reference: 'tx-ref' },
      { location: SOLANA_CHAIN, reference: 'tx-ref' },
      { location: 'kraken', reference: 'unique-id' },
    ])('should ask for the $reference of a swap on $location', async ({ location, reference }) => {
      await createWrapper();
      await locate(location);

      expect(has(`[data-testid=${reference}]`)).toBe(true);
    });

    it('should make a swap picked on an evm chain an evm swap once the chains load', async () => {
      set(evmLocations, []);
      await createWrapper();
      await locate('ethereum');
      expect(has('[data-testid=unique-id]')).toBe(true);

      set(evmLocations, ['ethereum']);
      await nextTick();

      expect(has('[data-testid=tx-ref]')).toBe(true);
    });

    it('should save a swap on solana as a solana swap, and keep the location open to move it again', async () => {
      await createWrapper();
      await locate(SOLANA_CHAIN);
      await fill('tx-ref', solanaTxRef);
      await fillRows();

      expect(wrapper.find<HTMLInputElement>('[data-testid=location] input').element.disabled).toBe(false);
      await expect(wrapper.vm.save()).resolves.toBe(true);
      expect(addHistoryEvent.mock.calls[0][0]).toMatchObject({ entryType: HistoryEventEntryType.SOLANA_SWAP_EVENT, txRef: solanaTxRef });
    });

    it('should clear the transaction and address moving from evm to solana, and keep the rest', async () => {
      await createWrapper();
      await locate('ethereum');
      await fill('tx-ref', evmTxRef);
      await fill('address', evmAddress);
      await fill('counterparty', 'uniswap-v3');
      await fillRows();

      await locate(SOLANA_CHAIN);
      await fill('tx-ref', solanaTxRef);

      await expect(wrapper.vm.save()).resolves.toBe(true);

      const payload = addHistoryEvent.mock.calls[0][0];
      expect(payload).toMatchObject({ counterparty: 'uniswap-v3', entryType: HistoryEventEntryType.SOLANA_SWAP_EVENT, txRef: solanaTxRef });
      expect(payload).not.toHaveProperty('address');
      expect(payload).toMatchObject({ spend: [{ amount: '0.1', asset: 'ETH' }] });
    });

    it('should not flag the signature a move to solana emptied, until it is touched', async () => {
      await createWrapper();
      await locate('ethereum');
      await fill('tx-ref', evmTxRef);
      await wrapper.find('[data-testid=tx-ref] input').trigger('blur');

      await locate(SOLANA_CHAIN);
      expect(wrapper.find('[data-testid=tx-ref] .details').text()).toBe('');

      await wrapper.find('[data-testid=tx-ref] input').trigger('blur');
      expect(wrapper.find('[data-testid=tx-ref] .details').text()).not.toBe('');
    });

    it('should count a switch as an edit', async () => {
      await createWrapper();

      await locate('ethereum');
      await nextTick();

      expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toEqual([true]);
    });

    it('should keep extra rows moving to a plain swap, and say a plain swap holds one a side', async () => {
      await createWrapper();
      await locate('ethereum');
      await wrapper.find('[data-testid=swap-sub-event-add][data-key=receive]').trigger('click');

      await locate('kraken');
      await expect(wrapper.vm.save()).resolves.toBe(false);
      await nextTick();

      expect(wrapper.findAll('[data-testid=sub-event-amount][data-key=receive]')).toHaveLength(2);
      expect(wrapper.find('[data-testid=swap-sub-event-list-error][data-key=receive]').text())
        .toBe('swap_event_form.validation.only_one');
    });
  });

  describe('the transaction lookup', () => {
    it('should run only for an evm swap being added', async () => {
      await createWrapper();
      await locate('ethereum');
      expect(lookup.enabled()).toBe(true);

      await locate(SOLANA_CHAIN);
      expect(lookup.enabled()).toBe(false);

      await locate('kraken');
      expect(lookup.enabled()).toBe(false);
    });

    it('should be reset when the kind changes, and kept moving between two evm chains', async () => {
      await createWrapper();
      await locate('ethereum');
      const resets = lookup.resets;

      await locate('optimism');
      expect(lookup.resets).toBe(resets);

      await locate(SOLANA_CHAIN);
      expect(lookup.resets).toBe(resets + 1);
    });

    it('should not run while an evm swap is edited', async () => {
      await createWrapper({
        eventsInGroup: [evmEvent('receive', 2, '300', 'USDC'), evmEvent('spend', 1, '0.1', 'ETH')],
        type: 'edit-group',
      });

      expect(lookup.enabled()).toBe(false);
    });
  });

  describe('rows', () => {
    function amounts(type: string): string[] {
      return wrapper.findAll<HTMLInputElement>(`[data-testid=sub-event-amount][data-key=${type}] input`).map(input => input.element.value);
    }

    it('should add a row to a side and remove it again', async () => {
      await createWrapper();
      await locate('ethereum');
      await wrapper.find('[data-testid=swap-sub-event-add][data-key=receive]').trigger('click');
      await wrapper.findAll('[data-testid=sub-event-amount][data-key=receive] input')[1].setValue('2');
      expect(amounts('receive')).toEqual(['', '2']);

      await wrapper.findAll('[data-testid=swap-sub-event-remove][data-key=receive]')[0].trigger('click');

      expect(amounts('receive')).toEqual(['2']);
    });

    async function fillFee(): Promise<void> {
      await fill('tx-ref', evmTxRef);
      await fillRows();
      await wrapper.find('[data-testid=has-fee] input').setValue(true);
      await wrapper.find('[data-testid=sub-event-amount][data-key=fee] input').setValue('0.005');
      await wrapper.find('[data-testid=sub-event-asset][data-key=fee] input').setValue('ETH');
    }

    it('should send no fee once the fee is turned off', async () => {
      await createWrapper();
      await locate('ethereum');
      await fillFee();

      await wrapper.find('[data-testid=has-fee] input').setValue(false);
      await nextTick();

      expect(amounts('fee')).toEqual([]);
      await expect(wrapper.vm.save()).resolves.toBe(true);
      expect(addHistoryEvent.mock.calls[0][0]).not.toHaveProperty('fee');
    });

    it('should start from an empty fee row when the fee is turned back on', async () => {
      await createWrapper();
      await locate('ethereum');
      await fillFee();

      await wrapper.find('[data-testid=has-fee] input').setValue(false);
      await nextTick();
      await wrapper.find('[data-testid=has-fee] input').setValue(true);
      await nextTick();

      await expect(wrapper.vm.save()).resolves.toBe(false);
      expect(addHistoryEvent).not.toHaveBeenCalled();
    });
  });

  describe('pointing the open form at another group', () => {
    it.each([
      {
        kind: HistoryEventEntryType.SWAP_EVENT,
        withFee: [plainEvent('spend', 10, '0.01', 'ETH'), plainEvent('receive', 11, '20', 'USD'), plainEvent('fee', 12, '1', 'USD')],
        withoutFee: [plainEvent('spend', 10, '0.01', 'ETH'), plainEvent('receive', 11, '20', 'USD')],
      },
      {
        kind: HistoryEventEntryType.EVM_SWAP_EVENT,
        withFee: [evmEvent('spend', 1, '0.1', 'ETH'), evmEvent('receive', 2, '300', 'USDC'), evmEvent('fee', 3, '0.005', 'ETH')],
        withoutFee: [evmEvent('spend', 1, '0.1', 'ETH'), evmEvent('receive', 2, '300', 'USDC')],
      },
    ] as const)('should show the new group\'s fee rows ($kind)', async ({ withFee, withoutFee }) => {
      await createWrapper({ eventsInGroup: [...withoutFee], type: 'edit-group' });

      await wrapper.setProps({ data: { eventsInGroup: [...withFee], type: 'edit-group' } });
      await vi.advanceTimersToNextTimerAsync();

      const fee = wrapper.findAll<HTMLInputElement>('[data-testid=sub-event-amount][data-key=fee] input');
      expect(fee.map(input => input.element.value)).toEqual([withFee[2].amount.toString()]);
    });
  });
});
