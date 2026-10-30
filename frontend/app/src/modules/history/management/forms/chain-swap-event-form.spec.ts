import type { ZodType } from 'zod';
import type { AddEvmSwapEventPayload, AddSolanaSwapEventPayload } from '@/modules/history/events/event-edit-payloads';
import type { EvmSwapEvent, SolanaSwapEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { emptyEvmSwapForm, type EvmSwapFormState, evmSwapSchema, evmSwapStateFromEvents, toEvmSwapPayload } from '@/modules/history/management/forms/evm-swap-event-form';
import { emptySolanaSwapForm, type SolanaSwapFormState, solanaSwapSchema, solanaSwapStateFromEvents, toSolanaSwapPayload } from '@/modules/history/management/forms/solana-swap-event-form';
import { emptySubEvent, type SwapSubEventState } from '@/modules/history/management/forms/swap/swap-sub-event';

/**
 * One chain swap kind, as the module that implements it exposes it.
 *
 * @remarks
 * The EVM and Solana swap modules differ in the transaction reference, the address format and
 * whether the form holds a location. Every other rule is shared, so both run through one suite.
 */
interface ChainSwapKind<TState extends SolanaSwapFormState, TEvent extends EvmSwapEvent | SolanaSwapEvent> {
  readonly name: string;
  readonly entryType: typeof HistoryEventEntryType.EVM_SWAP_EVENT | typeof HistoryEventEntryType.SOLANA_SWAP_EVENT;
  readonly txRef: string;
  readonly foreignTxRef: string;
  readonly address: string;
  readonly foreignAddress: string;
  readonly empty: () => TState;
  /** The fields a minimal valid swap needs on top of the empty form, other than its rows. */
  readonly required: Partial<TState>;
  /** The issue paths of an untouched form that are specific to this kind. */
  readonly ownRequiredPaths: readonly string[];
  /** The message a blank transaction reference reports, which names the kind's own reference. */
  readonly missingTxRefMessage: string;
  readonly schema: () => ZodType;
  readonly fromEvents: (events: TEvent[]) => TState;
  readonly toPayload: (state: TState) => AddEvmSwapEventPayload | AddSolanaSwapEventPayload;
  readonly event: (overrides: SwapEventOverrides) => TEvent;
}

/** The fields both chain swap events share, which is all a test varies. */
type SwapEventOverrides = Partial<Pick<EvmSwapEvent, 'amount' | 'asset' | 'eventSubtype' | 'identifier' | 'location' | 'userNotes'>>;

const evmTxRef = '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f';
const evmAddress = '0xA090e606E30bD747d4E6245a1517EbE430F0057e';
const solanaTxRef = '5wHu1qwD4kLwYqCEuNqTvhpFvGYRVYVEHVsdvR2v3Wg7fFyGxUWJTgL4wZ3Y1sM9RcYnPbLXZhKUqLNvV7kA8dQz';
const solanaAddress = '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8';

const evm: ChainSwapKind<EvmSwapFormState, EvmSwapEvent> = {
  address: evmAddress,
  empty: emptyEvmSwapForm,
  entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
  event: overrides => ({
    address: evmAddress,
    amount: bigNumberify('0.1'),
    asset: 'ETH',
    autoNotes: '',
    counterparty: 'uniswap-v3',
    entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
    eventSubtype: 'spend',
    eventType: 'trade',
    extraData: null,
    groupIdentifier: `1${evmTxRef}`,
    identifier: 3456,
    location: 'ethereum',
    locationLabel: evmAddress,
    sequenceIndex: 0,
    timestamp: 1742901211000,
    txRef: evmTxRef,
    userNotes: 'spend note',
    ...overrides,
  }),
  foreignAddress: solanaAddress,
  foreignTxRef: solanaTxRef,
  fromEvents: evmSwapStateFromEvents,
  name: 'evm',
  missingTxRefMessage: 'transactions.events.form.tx_hash.validation.non_empty',
  ownRequiredPaths: ['location'],
  required: { location: 'ethereum', txRef: evmTxRef },
  schema: evmSwapSchema,
  toPayload: toEvmSwapPayload,
  txRef: evmTxRef,
};

const solana: ChainSwapKind<SolanaSwapFormState, SolanaSwapEvent> = {
  address: solanaAddress,
  empty: emptySolanaSwapForm,
  entryType: HistoryEventEntryType.SOLANA_SWAP_EVENT,
  event: overrides => ({
    address: solanaAddress,
    amount: bigNumberify('0.1'),
    asset: 'SOL',
    autoNotes: '',
    counterparty: 'jupiter',
    entryType: HistoryEventEntryType.SOLANA_SWAP_EVENT,
    eventSubtype: 'spend',
    eventType: 'trade',
    extraData: null,
    groupIdentifier: `1${solanaTxRef}`,
    identifier: 3456,
    location: 'solana',
    locationLabel: solanaAddress,
    sequenceIndex: 0,
    timestamp: 1742901211000,
    txRef: solanaTxRef,
    userNotes: 'spend note',
    ...overrides,
  }),
  foreignAddress: evmAddress,
  foreignTxRef: evmTxRef,
  fromEvents: solanaSwapStateFromEvents,
  name: 'solana',
  missingTxRefMessage: 'transactions.events.form.signature.validation.non_empty',
  ownRequiredPaths: [],
  required: { txRef: solanaTxRef },
  schema: solanaSwapSchema,
  toPayload: toSolanaSwapPayload,
  txRef: solanaTxRef,
};

function row(amount: string, asset: string): SwapSubEventState {
  return { ...emptySubEvent(), amount, asset };
}

function chainSwapSuite<TState extends SolanaSwapFormState, TEvent extends EvmSwapEvent | SolanaSwapEvent>(
  kind: ChainSwapKind<TState, TEvent>,
): void {
  function validState(): TState {
    return {
      ...kind.empty(),
      ...kind.required,
      receive: [row('300', 'USDC')],
      spend: [row('0.1', 'ETH')],
    };
  }

  /** Sorted, because the order zod reports issues in is not part of the contract. */
  function issuePaths(state: TState): string[] {
    const result = kind.schema().safeParse(state);
    if (result.success)
      return [];
    return result.error.issues.map(issue => issue.path.join('.')).sort();
  }

  function issueMessages(state: TState, path: string): string[] {
    const result = kind.schema().safeParse(state);
    if (result.success)
      return [];
    return result.error.issues.filter(issue => issue.path.join('.') === path).map(issue => issue.message);
  }

  describe(`${kind.name} swap schema`, () => {
    it('should accept a minimally filled swap', () => {
      expect(issuePaths(validState())).toEqual([]);
    });

    it('should require both sides and a transaction reference, plus what the kind holds itself', () => {
      expect(issuePaths(kind.empty())).toEqual([
        ...kind.ownRequiredPaths,
        'receive.0.amount',
        'receive.0.asset',
        'spend.0.amount',
        'spend.0.asset',
        'txRef',
      ].sort());
    });

    it('should key a row error by its dotted path so rows do not share messages', () => {
      const state = validState();
      state.spend.push(emptySubEvent());

      expect(issuePaths(state)).toEqual(['spend.1.amount', 'spend.1.asset']);
    });

    it('should require a fee row only once the fee has been enabled', () => {
      expect(issuePaths({ ...validState(), hasFee: true })).toEqual(['fee']);
    });

    it('should not validate the rows of a disabled fee, which the form hides', () => {
      expect(issuePaths({ ...validState(), fee: [emptySubEvent()] })).toEqual([]);
    });

    it('should validate the rows of an enabled fee by their dotted path', () => {
      expect(issuePaths({ ...validState(), fee: [emptySubEvent()], hasFee: true })).toEqual(['fee.0.amount', 'fee.0.asset']);
    });

    it('should reject a transaction reference of the other chain', () => {
      expect(issuePaths({ ...validState(), txRef: kind.foreignTxRef })).toEqual(['txRef']);
    });

    it('should report a blank transaction reference once, as missing', () => {
      const messages = issueMessages({ ...validState(), txRef: '' }, 'txRef');

      expect(messages).toEqual([kind.missingTxRefMessage]);
    });

    it('should accept an address of its own chain and reject one of the other', () => {
      expect(issuePaths({ ...validState(), address: kind.address })).toEqual([]);
      expect(issuePaths({ ...validState(), address: kind.foreignAddress })).toEqual(['address']);
    });
  });

  describe(`${kind.name} swap state from events`, () => {
    it('should split a group into its spend, receive and fee rows', () => {
      const state = kind.fromEvents([
        kind.event({}),
        kind.event({ amount: bigNumberify('300'), asset: 'USDC', eventSubtype: 'receive', identifier: 3457, userNotes: 'receive note' }),
        kind.event({ amount: bigNumberify('0.005'), eventSubtype: 'fee', identifier: 3458, userNotes: undefined }),
      ]);

      expect(state.spend.map(item => [item.identifier, item.userNotes])).toEqual([[3456, 'spend note']]);
      expect(state.receive).toEqual([{ amount: '300', asset: 'USDC', identifier: 3457, locationLabel: kind.address, userNotes: 'receive note' }]);
      expect(state.fee).toEqual([{ amount: '0.005', asset: kind.event({}).asset, identifier: 3458, locationLabel: kind.address, userNotes: '' }]);
      expect(state.hasFee).toBe(true);
      expect(state.txRef).toBe(kind.txRef);
      expect(state.sequenceIndex).toBe('0');
    });

    it('should leave the fee disabled when the group has no fee event', () => {
      const state = kind.fromEvents([kind.event({}), kind.event({ eventSubtype: 'receive', identifier: 3457 })]);

      expect(state.hasFee).toBe(false);
      expect(state.fee).toEqual([]);
    });

    it('should refuse a group that is missing a side of the swap', () => {
      expect(() => kind.fromEvents([kind.event({})])).toThrow();
    });
  });

  describe(`${kind.name} swap payload`, () => {
    it('should omit the fee entirely while it is disabled', () => {
      expect(kind.toPayload({ ...validState(), fee: [row('0.005', 'ETH')] })).not.toHaveProperty('fee');
    });

    it('should include the fee rows once it is enabled', () => {
      expect(kind.toPayload({ ...validState(), fee: [row('0.005', 'ETH')], hasFee: true }).fee).toEqual([{ amount: '0.005', asset: 'ETH' }]);
    });

    it('should omit a blank address rather than send an empty string, and send a filled one', () => {
      expect(kind.toPayload(validState())).not.toHaveProperty('address');
      expect(kind.toPayload({ ...validState(), address: kind.address }).address).toBe(kind.address);
    });

    it('should not leak the hasFee toggle into the payload', () => {
      expect(kind.toPayload(validState())).not.toHaveProperty('hasFee');
    });

    it('should carry the entry type the backend dispatches on', () => {
      expect(kind.toPayload(validState()).entryType).toBe(kind.entryType);
    });
  });
}

chainSwapSuite(evm);
chainSwapSuite(solana);

describe('solana swap location', () => {
  it('should not send a location, which the solana swap endpoint does not take', () => {
    expect(toSolanaSwapPayload({ ...emptySolanaSwapForm(), txRef: solanaTxRef })).not.toHaveProperty('location');
  });

  it('should not read the location of the events it is seeded from', () => {
    const state = solanaSwapStateFromEvents([solana.event({}), solana.event({ eventSubtype: 'receive', identifier: 3457 })]);

    expect(state).not.toHaveProperty('location');
  });
});

describe('evm swap location', () => {
  it('should send the picked location and seed it from the group', () => {
    const state = evmSwapStateFromEvents([evm.event({ location: 'optimism' }), evm.event({ eventSubtype: 'receive', identifier: 3457 })]);

    expect(state.location).toBe('optimism');
    expect(toEvmSwapPayload(state).location).toBe('optimism');
  });
});
