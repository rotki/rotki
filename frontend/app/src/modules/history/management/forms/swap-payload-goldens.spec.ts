import type {
  AddEvmSwapEventPayload,
  AddSolanaSwapEventPayload,
  AddSwapEventPayload,
  EditSwapEventPayload,
} from '@/modules/history/events/event-edit-payloads';
import type { EvmSwapEvent, SolanaSwapEvent, SwapEvent } from '@/modules/history/events/schemas';
import type { PriceIntent } from '@/modules/history/management/forms/price-intent';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { omit } from 'es-toolkit';
import { describe, expect, it } from 'vitest';
import { type EvmSwapFormState, evmSwapStateFromEvents, toEvmSwapPayload } from '@/modules/history/management/forms/evm-swap-event-form';
import { type SolanaSwapFormState, solanaSwapStateFromEvents, toSolanaSwapPayload } from '@/modules/history/management/forms/solana-swap-event-form';
import {
  type SwapFormState,
  swapIdentifiers,
  swapStateFromEvents,
  toSwapEditPayload,
  toSwapPayload,
} from '@/modules/history/management/forms/swap-event-form';

const TIMESTAMP = 1742901211000;

const pendingPrice: PriceIntent = {
  fromAsset: 'ETH',
  price: '2000',
  timestampMs: TIMESTAMP,
  toAsset: 'USD',
};

const evmTxRef = '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f';
const evmAddress = '0xA090e606E30bD747d4E6245a1517EbE430F0057e';
const evmAccount = '0x6e15887E2CEC81434C16D587709f64603b39b541';
const solanaTxRef = '5wHu1qwD4kLwYqCEuNqTvhpFvGYRVYVEHVsdvR2v3Wg7fFyGxUWJTgL4wZ3Y1sM9RcYnPbLXZhKUqLNvV7kA8dQz';
const solanaAddress = '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8';
const solanaAccount = 'DRpbCBMxVnDK7maPM5tGv6MvB3v1sRMC86PZ8okm21hy';

describe('plain swap payload', () => {
  const filled: SwapFormState = {
    fees: [
      { amount: '1', asset: 'USD', userNotes: 'first fee' },
      { amount: '0.5', asset: 'BTC', userNotes: '' },
    ],
    hasFee: true,
    location: 'kraken',
    receiveAmount: '20',
    receiveAsset: 'USD',
    receiveNotes: 'receive note',
    receivePriceIntent: pendingPrice,
    spendAmount: '0.01',
    spendAsset: 'ETH',
    spendNotes: 'spend note',
    spendPriceIntent: pendingPrice,
    timestamp: TIMESTAMP,
    uniqueId: '',
  };

  const filledPayload: AddSwapEventPayload = {
    entryType: HistoryEventEntryType.SWAP_EVENT,
    fees: [{ amount: '1', asset: 'USD' }, { amount: '0.5', asset: 'BTC' }],
    location: 'kraken',
    receiveAmount: '20',
    receiveAsset: 'USD',
    spendAmount: '0.01',
    spendAsset: 'ETH',
    timestamp: TIMESTAMP,
    uniqueId: 'unique-id',
    userNotes: ['spend note', 'receive note', 'first fee', ''],
  };

  it('should send every field of a filled swap with its fees', () => {
    expect(toSwapPayload(filled, 'unique-id')).toEqual(filledPayload);
  });

  it('should send neither the fees nor their notes while the fee is disabled', () => {
    expect(toSwapPayload({ ...filled, hasFee: false }, 'unique-id')).toEqual({
      ...filledPayload,
      fees: undefined,
      userNotes: ['spend note', 'receive note'],
    });
  });

  it('should send an edited group back as it was loaded, addressed by its identifiers', () => {
    const base = {
      autoNotes: '',
      entryType: HistoryEventEntryType.SWAP_EVENT,
      eventType: 'trade',
      extraData: null,
      groupIdentifier: 'group',
      location: 'kraken',
      locationLabel: null,
      sequenceIndex: 0,
      timestamp: TIMESTAMP,
    } satisfies Partial<SwapEvent>;
    const events: SwapEvent[] = [
      { ...base, amount: bigNumberify('1'), asset: 'USD', eventSubtype: 'fee', identifier: 12, userNotes: 'fee note' },
      { ...base, amount: bigNumberify('20'), asset: 'USD', eventSubtype: 'receive', identifier: 11, userNotes: 'receive note' },
      { ...base, amount: bigNumberify('0.01'), asset: 'ETH', eventSubtype: 'spend', identifier: 10, userNotes: 'spend note' },
    ];

    const payload = toSwapPayload(swapStateFromEvents(events), 'ignored');

    expect(toSwapEditPayload(payload, swapIdentifiers(events))).toEqual({
      entryType: HistoryEventEntryType.SWAP_EVENT,
      fees: [{ amount: '1', asset: 'USD' }],
      identifiers: [10, 11, 12],
      location: 'kraken',
      receiveAmount: '20',
      receiveAsset: 'USD',
      spendAmount: '0.01',
      spendAsset: 'ETH',
      timestamp: TIMESTAMP,
      userNotes: ['spend note', 'receive note', 'fee note'],
    } satisfies EditSwapEventPayload);
  });
});

describe('evm swap payload', () => {
  const filled: EvmSwapFormState = {
    address: evmAddress,
    counterparty: 'uniswap-v3',
    fee: [{ amount: '0.005', asset: 'ETH', locationLabel: evmAccount, userNotes: 'gas' }],
    hasFee: true,
    location: 'optimism',
    receive: [
      { amount: '150', asset: 'USDC', identifier: 21, locationLabel: evmAccount, userNotes: 'first half' },
      { amount: '150', asset: 'USDC', locationLabel: '', userNotes: '' },
    ],
    sequenceIndex: '4',
    spend: [{ amount: '0.1', asset: 'ETH', identifier: 20, locationLabel: evmAccount, priceIntent: pendingPrice, userNotes: 'spend note' }],
    timestamp: TIMESTAMP,
    txRef: evmTxRef,
  };

  const filledPayload: AddEvmSwapEventPayload = {
    address: evmAddress,
    counterparty: 'uniswap-v3',
    entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
    fee: [{ amount: '0.005', asset: 'ETH', locationLabel: evmAccount, userNotes: 'gas' }],
    location: 'optimism',
    receive: [
      { amount: '150', asset: 'USDC', identifier: 21, locationLabel: evmAccount, userNotes: 'first half' },
      { amount: '150', asset: 'USDC' },
    ],
    sequenceIndex: '4',
    spend: [{ amount: '0.1', asset: 'ETH', identifier: 20, locationLabel: evmAccount, userNotes: 'spend note' }],
    timestamp: TIMESTAMP,
    txRef: evmTxRef,
  };

  it('should send every field of a filled swap with its fee', () => {
    expect(toEvmSwapPayload(filled)).toEqual(filledPayload);
  });

  it('should send neither the fee nor an empty address when they are off', () => {
    expect(toEvmSwapPayload({ ...filled, address: '', hasFee: false })).toEqual(omit(filledPayload, ['address', 'fee']));
  });

  it('should send a loaded group back as it was loaded', () => {
    const base = {
      address: evmAddress,
      autoNotes: '',
      counterparty: 'uniswap-v3',
      entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
      eventType: 'trade',
      extraData: null,
      groupIdentifier: `10${evmTxRef}`,
      location: 'optimism',
      locationLabel: evmAccount,
      sequenceIndex: 4,
      timestamp: TIMESTAMP,
      txRef: evmTxRef,
    } satisfies Partial<EvmSwapEvent>;
    const events: EvmSwapEvent[] = [
      { ...base, amount: bigNumberify('0.1'), asset: 'ETH', eventSubtype: 'spend', identifier: 20, userNotes: 'spend note' },
      { ...base, amount: bigNumberify('300'), asset: 'USDC', eventSubtype: 'receive', identifier: 21 },
      { ...base, amount: bigNumberify('0.005'), asset: 'ETH', eventSubtype: 'fee', identifier: 22, userNotes: 'gas' },
    ];

    expect(toEvmSwapPayload(evmSwapStateFromEvents(events))).toEqual({
      address: evmAddress,
      counterparty: 'uniswap-v3',
      entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
      fee: [{ amount: '0.005', asset: 'ETH', identifier: 22, locationLabel: evmAccount, userNotes: 'gas' }],
      location: 'optimism',
      receive: [{ amount: '300', asset: 'USDC', identifier: 21, locationLabel: evmAccount }],
      sequenceIndex: '4',
      spend: [{ amount: '0.1', asset: 'ETH', identifier: 20, locationLabel: evmAccount, userNotes: 'spend note' }],
      timestamp: TIMESTAMP,
      txRef: evmTxRef,
    } satisfies AddEvmSwapEventPayload);
  });
});

describe('solana swap payload', () => {
  const filled: SolanaSwapFormState = {
    address: solanaAddress,
    counterparty: 'jupiter',
    fee: [{ amount: '0.00001', asset: 'SOL', locationLabel: solanaAccount, userNotes: 'network fee' }],
    hasFee: true,
    receive: [{ amount: '300', asset: 'USDC', locationLabel: solanaAccount, userNotes: '' }],
    sequenceIndex: '2',
    spend: [{ amount: '1.5', asset: 'SOL', identifier: 30, locationLabel: solanaAccount, priceIntent: pendingPrice, userNotes: 'spend note' }],
    timestamp: TIMESTAMP,
    txRef: solanaTxRef,
  };

  const filledPayload: AddSolanaSwapEventPayload = {
    address: solanaAddress,
    counterparty: 'jupiter',
    entryType: HistoryEventEntryType.SOLANA_SWAP_EVENT,
    fee: [{ amount: '0.00001', asset: 'SOL', locationLabel: solanaAccount, userNotes: 'network fee' }],
    receive: [{ amount: '300', asset: 'USDC', locationLabel: solanaAccount }],
    sequenceIndex: '2',
    spend: [{ amount: '1.5', asset: 'SOL', identifier: 30, locationLabel: solanaAccount, userNotes: 'spend note' }],
    timestamp: TIMESTAMP,
    txRef: solanaTxRef,
  };

  it('should send every field of a filled swap with its fee, and no location', () => {
    expect(toSolanaSwapPayload(filled)).toEqual(filledPayload);
  });

  it('should send neither the fee nor an empty address when they are off', () => {
    expect(toSolanaSwapPayload({ ...filled, address: '', hasFee: false })).toEqual(omit(filledPayload, ['address', 'fee']));
  });

  it('should send a loaded group back as it was loaded', () => {
    const base = {
      address: solanaAddress,
      autoNotes: '',
      counterparty: 'jupiter',
      entryType: HistoryEventEntryType.SOLANA_SWAP_EVENT,
      eventType: 'trade',
      extraData: null,
      groupIdentifier: `10${solanaTxRef}`,
      location: 'solana',
      locationLabel: solanaAccount,
      sequenceIndex: 2,
      timestamp: TIMESTAMP,
      txRef: solanaTxRef,
    } satisfies Partial<SolanaSwapEvent>;
    const events: SolanaSwapEvent[] = [
      { ...base, amount: bigNumberify('1.5'), asset: 'SOL', eventSubtype: 'spend', identifier: 30, userNotes: 'spend note' },
      { ...base, amount: bigNumberify('300'), asset: 'USDC', eventSubtype: 'receive', identifier: 31 },
      { ...base, amount: bigNumberify('0.00001'), asset: 'SOL', eventSubtype: 'fee', identifier: 32, userNotes: 'network fee' },
    ];

    expect(toSolanaSwapPayload(solanaSwapStateFromEvents(events))).toEqual({
      address: solanaAddress,
      counterparty: 'jupiter',
      entryType: HistoryEventEntryType.SOLANA_SWAP_EVENT,
      fee: [{ amount: '0.00001', asset: 'SOL', identifier: 32, locationLabel: solanaAccount, userNotes: 'network fee' }],
      receive: [{ amount: '300', asset: 'USDC', identifier: 31, locationLabel: solanaAccount }],
      sequenceIndex: '2',
      spend: [{ amount: '1.5', asset: 'SOL', identifier: 30, locationLabel: solanaAccount, userNotes: 'spend note' }],
      timestamp: TIMESTAMP,
      txRef: solanaTxRef,
    } satisfies AddSolanaSwapEventPayload);
  });
});
