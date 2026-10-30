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
import { SOLANA_CHAIN } from '@/modules/assets/types';
import {
  emptySwapForm,
  type SwapFormState,
  swapIdentifiers,
  swapSchema,
  swapServerErrorPaths,
  swapStateForGroupAdd,
  swapStateFromEvents,
  switchSwapKind,
  toSwapEditPayload,
  toSwapPayload,
} from '@/modules/history/management/forms/swap-event-form';
import { emptySubEvent, type SwapSubEventState } from '@/modules/history/management/forms/swap/swap-sub-event';

const TIMESTAMP = 1742901211000;

/** Only a new plain swap asks for a unique id, so the chain kinds' goldens fail loudly if it is read. */
function noUniqueId(): string {
  throw new Error('a chain swap needs no unique id');
}

function row(amount: string, asset: string, extra: Partial<SwapSubEventState> = {}): SwapSubEventState {
  return { ...emptySubEvent(), amount, asset, ...extra };
}

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
    ...emptySwapForm(HistoryEventEntryType.SWAP_EVENT),
    fee: [row('1', 'USD', { userNotes: 'first fee' }), row('0.5', 'BTC')],
    hasFee: true,
    location: 'kraken',
    receive: [row('20', 'USD', { priceIntent: pendingPrice, userNotes: 'receive note' })],
    spend: [row('0.01', 'ETH', { priceIntent: pendingPrice, userNotes: 'spend note' })],
    timestamp: TIMESTAMP,
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
    expect(toSwapPayload(filled, () => 'unique-id')).toEqual(filledPayload);
  });

  it('should send neither the fees nor their notes while the fee is disabled', () => {
    expect(toSwapPayload({ ...filled, hasFee: false }, () => 'unique-id')).toEqual({
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

    const payload = toSwapPayload(swapStateFromEvents(events), () => 'ignored');

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
  const filled: SwapFormState = {
    address: evmAddress,
    counterparty: 'uniswap-v3',
    fee: [{ amount: '0.005', asset: 'ETH', locationLabel: evmAccount, userNotes: 'gas' }],
    hasFee: true,
    kind: HistoryEventEntryType.EVM_SWAP_EVENT,
    location: 'optimism',
    receive: [
      { amount: '150', asset: 'USDC', identifier: 21, locationLabel: evmAccount, userNotes: 'first half' },
      { amount: '150', asset: 'USDC', locationLabel: '', userNotes: '' },
    ],
    sequenceIndex: '4',
    spend: [{ amount: '0.1', asset: 'ETH', identifier: 20, locationLabel: evmAccount, priceIntent: pendingPrice, userNotes: 'spend note' }],
    timestamp: TIMESTAMP,
    txRef: evmTxRef,
    uniqueId: '',
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
    expect(toSwapPayload(filled, noUniqueId)).toEqual(filledPayload);
  });

  it('should send neither the fee nor an empty address when they are off', () => {
    expect(toSwapPayload({ ...filled, address: '', hasFee: false }, noUniqueId)).toEqual(omit(filledPayload, ['address', 'fee']));
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

    expect(toSwapPayload(swapStateFromEvents(events), noUniqueId)).toEqual({
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
  const filled: SwapFormState = {
    address: solanaAddress,
    counterparty: 'jupiter',
    fee: [{ amount: '0.00001', asset: 'SOL', locationLabel: solanaAccount, userNotes: 'network fee' }],
    hasFee: true,
    kind: HistoryEventEntryType.SOLANA_SWAP_EVENT,
    location: SOLANA_CHAIN,
    receive: [{ amount: '300', asset: 'USDC', locationLabel: solanaAccount, userNotes: '' }],
    sequenceIndex: '2',
    spend: [{ amount: '1.5', asset: 'SOL', identifier: 30, locationLabel: solanaAccount, priceIntent: pendingPrice, userNotes: 'spend note' }],
    timestamp: TIMESTAMP,
    txRef: solanaTxRef,
    uniqueId: '',
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
    expect(toSwapPayload(filled, noUniqueId)).toEqual(filledPayload);
  });

  it('should send neither the fee nor an empty address when they are off', () => {
    expect(toSwapPayload({ ...filled, address: '', hasFee: false }, noUniqueId)).toEqual(omit(filledPayload, ['address', 'fee']));
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

    expect(toSwapPayload(swapStateFromEvents(events), noUniqueId)).toEqual({
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

function plainEvent(overrides: Partial<SwapEvent>): SwapEvent {
  return {
    amount: bigNumberify('0.01'),
    asset: 'ETH',
    autoNotes: '',
    entryType: HistoryEventEntryType.SWAP_EVENT,
    eventSubtype: 'spend',
    eventType: 'trade',
    extraData: null,
    groupIdentifier: 'group',
    identifier: 2737,
    location: 'binance',
    locationLabel: null,
    sequenceIndex: 0,
    timestamp: TIMESTAMP,
    userNotes: 'spend note',
    ...overrides,
  };
}

function validPlain(): SwapFormState {
  return {
    ...emptySwapForm(HistoryEventEntryType.SWAP_EVENT),
    location: 'binance',
    receive: [row('20', 'USD')],
    spend: [row('0.01', 'ETH')],
  };
}

/** Sorted, because the order zod reports issues in is not part of the contract. */
function issuePaths(state: SwapFormState): string[] {
  const result = swapSchema().safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.path.join('.')).sort();
}

describe('plain swap schema', () => {
  it('should accept a minimally filled swap', () => {
    expect(issuePaths(validPlain())).toEqual([]);
  });

  it('should require a location and both sides of the swap', () => {
    expect(issuePaths(emptySwapForm(HistoryEventEntryType.SWAP_EVENT)))
      .toEqual(['location', 'receive.0.amount', 'receive.0.asset', 'spend.0.amount', 'spend.0.asset']);
  });

  it('should hold one asset on each side', () => {
    expect(issuePaths({ ...validPlain(), spend: [row('0.01', 'ETH'), row('1', 'BTC')] })).toEqual(['spend']);
  });

  it('should require a fee row once the fee has been enabled', () => {
    expect(issuePaths({ ...validPlain(), hasFee: true })).toEqual(['fee']);
  });

  it('should validate the rows of an enabled fee by their dotted path, and ignore those of a disabled one', () => {
    expect(issuePaths({ ...validPlain(), fee: [emptySubEvent()], hasFee: true })).toEqual(['fee.0.amount', 'fee.0.asset']);
    expect(issuePaths({ ...validPlain(), fee: [emptySubEvent()] })).toEqual([]);
  });

  it('should not ask a plain swap for the chain fields it does not have', () => {
    expect(issuePaths({ ...validPlain(), sequenceIndex: '', txRef: 'not a hash' })).toEqual([]);
  });
});

describe('plain swap state from events', () => {
  it('should put each note on the row it belongs to', () => {
    const state = swapStateFromEvents([
      plainEvent({}),
      plainEvent({ amount: bigNumberify('20'), asset: 'USD', eventSubtype: 'receive', identifier: 2738, userNotes: 'receive note' }),
      plainEvent({ amount: bigNumberify('1'), asset: 'USD', eventSubtype: 'fee', identifier: 2739, userNotes: 'fee note' }),
    ]);

    expect(state.kind).toBe(HistoryEventEntryType.SWAP_EVENT);
    expect(state.spend).toEqual([row('0.01', 'ETH', { userNotes: 'spend note' })]);
    expect(state.receive).toEqual([row('20', 'USD', { userNotes: 'receive note' })]);
    expect(state.fee).toEqual([row('1', 'USD', { userNotes: 'fee note' })]);
    expect(state.hasFee).toBe(true);
  });

  it('should refuse a group that is missing a side of the swap', () => {
    expect(() => swapStateFromEvents([plainEvent({})])).toThrow();
  });
});

describe('swap identifiers', () => {
  it('should order a plain swap\'s identifiers as spend, receive, then the fees', () => {
    const fees = [plainEvent({ eventSubtype: 'fee', identifier: 2739 }), plainEvent({ eventSubtype: 'fee', identifier: 2740 })];

    expect(swapIdentifiers([fees[1], plainEvent({ eventSubtype: 'receive', identifier: 2738 }), fees[0], plainEvent({})]))
      .toEqual([2737, 2738, 2740, 2739]);
  });

  it('should keep a chain swap\'s identifiers in the group\'s own order', () => {
    const base = {
      address: evmAddress,
      amount: bigNumberify('1'),
      asset: 'ETH',
      autoNotes: '',
      counterparty: null,
      entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
      eventType: 'trade',
      extraData: null,
      groupIdentifier: 'group',
      location: 'ethereum',
      locationLabel: evmAccount,
      sequenceIndex: 0,
      timestamp: TIMESTAMP,
      txRef: evmTxRef,
    } satisfies Partial<EvmSwapEvent>;
    const events: EvmSwapEvent[] = [
      { ...base, eventSubtype: 'fee', identifier: 3 },
      { ...base, eventSubtype: 'receive', identifier: 2 },
      { ...base, eventSubtype: 'spend', identifier: 1 },
    ];

    expect(swapIdentifiers(events)).toEqual([3, 2, 1]);
  });
});

describe('swap payload', () => {
  it('should send the unique id the user typed for a new plain swap', () => {
    expect(toSwapPayload({ ...validPlain(), uniqueId: 'typed' }, () => 'generated')).toMatchObject({ uniqueId: 'typed' });
  });

  it('should generate a unique id for a new plain swap left without one', () => {
    expect(toSwapPayload(validPlain(), () => 'generated')).toMatchObject({ uniqueId: 'generated' });
  });

  it('should address a chain swap edit by identifiers and keep the rest of its payload', () => {
    const payload = toSwapPayload({ ...emptySwapForm(HistoryEventEntryType.EVM_SWAP_EVENT), location: 'ethereum', txRef: evmTxRef }, noUniqueId);

    expect(toSwapEditPayload(payload, [1, 2])).toEqual({ ...payload, identifiers: [1, 2] });
  });
});

describe('a swap added into an existing transaction', () => {
  const group = { location: 'optimism', timestamp: TIMESTAMP, txRef: evmTxRef };

  it('should take the transaction\'s location, reference, time and the next sequence index', () => {
    expect(swapStateForGroupAdd(HistoryEventEntryType.EVM_SWAP_EVENT, group, '7')).toMatchObject({
      kind: HistoryEventEntryType.EVM_SWAP_EVENT,
      location: 'optimism',
      sequenceIndex: '7',
      timestamp: TIMESTAMP,
      txRef: evmTxRef,
    });
  });

  it('should keep a solana swap on solana whatever the transaction says', () => {
    expect(swapStateForGroupAdd(HistoryEventEntryType.SOLANA_SWAP_EVENT, { ...group, txRef: solanaTxRef }, '2').location)
      .toBe(SOLANA_CHAIN);
  });

  it('should refuse a plain swap, which has no transaction to add into', () => {
    expect(() => swapStateForGroupAdd(HistoryEventEntryType.SWAP_EVENT, group, '1')).toThrow();
  });
});

describe('switching the swap kind', () => {
  function evmState(): SwapFormState {
    return {
      ...emptySwapForm(HistoryEventEntryType.EVM_SWAP_EVENT),
      address: evmAddress,
      counterparty: 'uniswap-v3',
      location: 'ethereum',
      receive: [row('300', 'USDC'), row('1', 'DAI')],
      sequenceIndex: '4',
      spend: [row('0.1', 'ETH')],
      timestamp: TIMESTAMP,
      txRef: evmTxRef,
    };
  }

  it('should clear the transaction and address moving between EVM and Solana, and keep the rest', () => {
    const state = switchSwapKind(evmState(), HistoryEventEntryType.SOLANA_SWAP_EVENT);

    expect(state).toEqual({
      ...evmState(),
      address: '',
      kind: HistoryEventEntryType.SOLANA_SWAP_EVENT,
      location: SOLANA_CHAIN,
      txRef: '',
    });
  });

  it('should keep every row moving to a plain swap, which then holds too many', () => {
    const state = switchSwapKind(evmState(), HistoryEventEntryType.SWAP_EVENT);

    expect(state.receive).toEqual(evmState().receive);
    expect(state.location).toBe('');
    expect(issuePaths({ ...state, location: 'binance' })).toEqual(['receive']);
  });

  it('should leave the state alone when the kind does not change', () => {
    const state = evmState();

    expect(switchSwapKind(state, HistoryEventEntryType.EVM_SWAP_EVENT)).toBe(state);
  });
});

describe('swap server error paths', () => {
  it('should move a plain swap\'s flat field errors onto its rows', () => {
    expect(swapServerErrorPaths(HistoryEventEntryType.SWAP_EVENT, {
      fees: ['bad fee'],
      location: ['bad location'],
      receiveAsset: ['unknown asset'],
      spendAmount: ['too small'],
      userNotes: ['too long'],
    })).toEqual({
      'fee': ['bad fee'],
      'location': ['bad location'],
      'receive.0.asset': ['unknown asset'],
      'spend.0.amount': ['too small'],
      'spend.0.userNotes': ['too long'],
    });
  });

  it('should leave a chain swap\'s errors where the endpoint put them', () => {
    const errors = { 'spend.0.amount': ['too small'] };

    expect(swapServerErrorPaths(HistoryEventEntryType.EVM_SWAP_EVENT, errors)).toBe(errors);
  });
});
