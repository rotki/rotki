import type { SolanaSwapEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { emptySolanaSwapForm, type SolanaSwapFormState, solanaSwapSchema, solanaSwapStateFromEvents, toSolanaSwapPayload } from '@/modules/history/management/forms/solana-swap-event-form';

const txRef = '5wHu1qwD4kLwYqCEuNqTvhpFvGYRVYVEHVsdvR2v3Wg7fFyGxUWJTgL4wZ3Y1sM9RcYnPbLXZhKUqLNvV7kA8dQz';
const address = '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8';

function validState(): SolanaSwapFormState {
  return {
    ...emptySolanaSwapForm(),
    receive: [{ amount: '300', asset: 'USDC', locationLabel: '', userNotes: '' }],
    spend: [{ amount: '0.1', asset: 'SOL', locationLabel: '', userNotes: '' }],
    txRef,
  };
}

/** Sorted, because the order zod reports issues in is not part of the contract. */
function issuePaths(state: SolanaSwapFormState): string[] {
  const result = solanaSwapSchema().safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.path.join('.')).sort();
}

function swapEvent(overrides: Partial<SolanaSwapEvent>): SolanaSwapEvent {
  const base = {
    address,
    amount: bigNumberify('0.1'),
    asset: 'SOL',
    autoNotes: '',
    counterparty: 'jupiter',
    entryType: HistoryEventEntryType.SOLANA_SWAP_EVENT,
    eventSubtype: 'spend',
    eventType: 'trade',
    extraData: null,
    groupIdentifier: `1${txRef}`,
    identifier: 3456,
    location: 'solana',
    locationLabel: address,
    sequenceIndex: 0,
    timestamp: 1742901211000,
    txRef,
    userNotes: 'spend note',
  } satisfies SolanaSwapEvent;

  return { ...base, ...overrides };
}

describe('solanaSwapSchema', () => {
  it('should accept a minimally filled swap', () => {
    expect(issuePaths(validState())).toEqual([]);
  });

  it('should not validate a location, which a solana swap does not hold', () => {
    expect(issuePaths(emptySolanaSwapForm())).toEqual([
      'receive.0.amount',
      'receive.0.asset',
      'spend.0.amount',
      'spend.0.asset',
      'txRef',
    ]);
  });

  it('should reject a signature that is not a solana one', () => {
    expect(issuePaths({ ...validState(), txRef: '0xnope' })).toEqual(['txRef']);
  });

  it('should require a fee row only once the fee has been enabled', () => {
    expect(issuePaths({ ...validState(), hasFee: true })).toEqual(['fee']);
  });

  it('should validate the address against the solana format', () => {
    expect(issuePaths({ ...validState(), address })).toEqual([]);
    expect(issuePaths({ ...validState(), address: '0xA090e606E30bD747d4E6245a1517EbE430F0057e' }))
      .toEqual(['address']);
  });
});

describe('solanaSwapStateFromEvents', () => {
  it('should split a group into its spend, receive and fee rows', () => {
    const state = solanaSwapStateFromEvents([
      swapEvent({}),
      swapEvent({ amount: bigNumberify('300'), asset: 'USDC', eventSubtype: 'receive', identifier: 3457 }),
      swapEvent({ amount: bigNumberify('0.00001'), eventSubtype: 'fee', identifier: 3458 }),
    ]);

    expect(state.hasFee).toBe(true);
    expect(state.fee).toEqual([{
      amount: '0.00001',
      asset: 'SOL',
      identifier: 3458,
      locationLabel: address,
      userNotes: 'spend note',
    }]);
    expect(state.txRef).toBe(txRef);
  });
});

describe('toSolanaSwapPayload', () => {
  it('should not send a location, which the solana swap endpoint does not take', () => {
    expect(toSolanaSwapPayload(validState())).not.toHaveProperty('location');
  });

  it('should omit the fee entirely when it is disabled', () => {
    const state = validState();
    state.fee = [{ amount: '0.00001', asset: 'SOL', locationLabel: '', userNotes: '' }];

    expect(toSolanaSwapPayload(state)).not.toHaveProperty('fee');
  });

  it('should carry the entry type the backend dispatches on', () => {
    expect(toSolanaSwapPayload(validState()).entryType).toBe(HistoryEventEntryType.SOLANA_SWAP_EVENT);
  });
});
