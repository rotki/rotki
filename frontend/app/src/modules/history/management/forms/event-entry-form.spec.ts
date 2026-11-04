import { HistoryEventEntryType } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { SOLANA_CHAIN } from '@/modules/assets/types';
import {
  emptyEventEntryForm,
  type EventEntryFormState,
  eventEntrySchema,
  eventKindAt,
  relocateEventEntry,
} from '@/modules/history/management/forms/event-entry-form';

const evmTxRef = '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f';
const evmAddress = '0xA090e606E30bD747d4E6245a1517EbE430F0057e';
const signature = '5wHu1qwD4kLwYqCEuNqTvhpFvGYRVYVEHVsdvR2v3Wg7fFyGxUWJTgL4wZ3Y1sM9RcYnPbLXZhKUqLNvV7kA8dQz';
const solanaAddress = '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8';
const bitcoinTxId = '4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b';

/** The chains an evm event can be on, as the supported chains name them. */
const evmLocations = ['ethereum', 'optimism'];

const counterparties = (): string[] => ['uniswap-v3', 'jupiter', 'bitcoin-core'];

function filled(kind: EventEntryFormState['kind'], overrides: Partial<EventEntryFormState> = {}): EventEntryFormState {
  return {
    ...emptyEventEntryForm(kind, { location: 'ethereum', nextSequenceId: '0' }),
    amount: '1',
    asset: 'ETH',
    eventSubtype: 'fee',
    eventType: 'spend',
    timestamp: 1742901211000,
    ...overrides,
  };
}

/** Sorted, because the order zod reports issues in is not part of the contract. */
function issuePaths(state: EventEntryFormState, editing = false): string[] {
  const result = eventEntrySchema(editing, counterparties).safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.path.join('.')).sort();
}

describe('plain and bank event schema', () => {
  it.each([HistoryEventEntryType.HISTORY_EVENT, HistoryEventEntryType.BANK_TRANSACTION_EVENT])('should accept a filled %s', (kind) => {
    expect(issuePaths(filled(kind, { location: 'kraken' }))).toEqual([]);
  });

  it('should require the asset, event type and location', () => {
    expect(issuePaths({ ...emptyEventEntryForm(HistoryEventEntryType.HISTORY_EVENT, { location: '', nextSequenceId: '0' }) }))
      .toEqual(['asset', 'eventType', 'location']);
  });

  it('should not ask a plain event for the chain fields it does not have', () => {
    expect(issuePaths(filled(HistoryEventEntryType.HISTORY_EVENT, { counterparty: 'made-up', txRef: 'nope' }))).toEqual([]);
  });

  it('should require a group identifier only while editing', () => {
    expect(issuePaths(filled(HistoryEventEntryType.HISTORY_EVENT), true)).toEqual(['groupIdentifier']);
  });
});

describe('evm event schema', () => {
  function validState(): EventEntryFormState {
    return filled(HistoryEventEntryType.EVM_EVENT, { txRef: evmTxRef });
  }

  it('should accept a filled form', () => {
    expect(issuePaths(validState())).toEqual([]);
  });

  it('should require the asset, event type and transaction hash', () => {
    expect(issuePaths(emptyEventEntryForm(HistoryEventEntryType.EVM_EVENT, { location: 'ethereum', nextSequenceId: '0' })))
      .toEqual(['asset', 'eventType', 'txRef']);
  });

  it('should accept a counterparty that is known, an address, or blank', () => {
    for (const counterparty of ['', 'uniswap-v3', evmAddress])
      expect(issuePaths({ ...validState(), counterparty })).toEqual([]);
  });

  it('should reject a counterparty that is neither', () => {
    expect(issuePaths({ ...validState(), counterparty: 'made-up' })).toEqual(['counterparty']);
  });

  it('should require a group identifier only while editing', () => {
    expect(issuePaths(validState(), true)).toEqual(['groupIdentifier']);
  });
});

describe('solana event schema', () => {
  function validState(): EventEntryFormState {
    return filled(HistoryEventEntryType.SOLANA_EVENT, { asset: 'SOL', txRef: signature });
  }

  it('should accept a filled form', () => {
    expect(issuePaths(validState())).toEqual([]);
  });

  it('should require the asset, event type and signature', () => {
    expect(issuePaths(emptyEventEntryForm(HistoryEventEntryType.SOLANA_EVENT, { location: 'kraken', nextSequenceId: '0' })))
      .toEqual(['asset', 'eventType', 'txRef']);
  });

  it('should reject an evm transaction hash and an evm address', () => {
    expect(issuePaths({ ...validState(), address: evmAddress, txRef: evmTxRef })).toEqual(['address', 'txRef']);
  });

  it('should accept a counterparty that is known, or blank', () => {
    for (const counterparty of ['', 'jupiter'])
      expect(issuePaths({ ...validState(), counterparty })).toEqual([]);
  });

  it('should reject a counterparty that is not known', () => {
    expect(issuePaths({ ...validState(), counterparty: 'made-up' })).toEqual(['counterparty']);
  });

  it('should keep a new solana event on solana whatever location it was given', () => {
    expect(emptyEventEntryForm(HistoryEventEntryType.SOLANA_EVENT, { location: 'kraken', nextSequenceId: '0' }).location).toBe(SOLANA_CHAIN);
  });
});

describe('bitcoin event schema', () => {
  function validState(): EventEntryFormState {
    return filled(HistoryEventEntryType.BITCOIN_EVENT, { txRef: bitcoinTxId });
  }

  it('should accept a filled form', () => {
    expect(issuePaths(validState())).toEqual([]);
  });

  it('should not validate an asset, which the chain decides', () => {
    expect(issuePaths(emptyEventEntryForm(HistoryEventEntryType.BITCOIN_EVENT, { location: 'kraken', nextSequenceId: '0' })))
      .toEqual(['eventType', 'txRef']);
  });

  it('should reject a transaction id that is not a bitcoin one', () => {
    expect(issuePaths({ ...validState(), txRef: '0xnope' })).toEqual(['txRef']);
  });

  it('should open a new bitcoin event on bitcoin', () => {
    expect(emptyEventEntryForm(HistoryEventEntryType.BITCOIN_EVENT, { location: 'kraken', nextSequenceId: '0' }).location).toBe('bitcoin');
  });
});

describe('the event kind a location implies', () => {
  it.each([
    { kind: HistoryEventEntryType.EVM_EVENT, location: 'optimism' },
    { kind: HistoryEventEntryType.SOLANA_EVENT, location: SOLANA_CHAIN },
    { kind: HistoryEventEntryType.BITCOIN_EVENT, location: 'bitcoin' },
    { kind: HistoryEventEntryType.BITCOIN_EVENT, location: 'bitcoin cash' },
    { kind: HistoryEventEntryType.HISTORY_EVENT, location: 'kraken' },
    { kind: HistoryEventEntryType.HISTORY_EVENT, location: '' },
  ])('should make an event on "$location" a $kind', ({ kind, location }) => {
    expect(eventKindAt(location, evmLocations)).toBe(kind);
  });
});

describe('moving an event being added to another location', () => {
  function evmState(): EventEntryFormState {
    return filled(HistoryEventEntryType.EVM_EVENT, { address: evmAddress, counterparty: 'uniswap-v3', txRef: evmTxRef });
  }

  function relocate(state: EventEntryFormState, location: string): EventEntryFormState {
    return relocateEventEntry(state, location, evmLocations);
  }

  it('should clear the transaction and address moving from an evm chain to solana, and keep the rest', () => {
    expect(relocate(evmState(), SOLANA_CHAIN)).toEqual({
      ...evmState(),
      address: '',
      kind: HistoryEventEntryType.SOLANA_EVENT,
      location: SOLANA_CHAIN,
      txRef: '',
    });
  });

  it('should keep the transaction and address moving between two evm chains', () => {
    expect(relocate(evmState(), 'optimism')).toEqual({ ...evmState(), location: 'optimism' });
  });

  it('should clear an evm hash moving to bitcoin, and keep the address unseen', () => {
    expect(relocate(evmState(), 'bitcoin')).toMatchObject({ address: evmAddress, kind: HistoryEventEntryType.BITCOIN_EVENT, txRef: '' });
  });

  it('should not carry an evm transaction or address into a solana event through a plain one', () => {
    const state = relocate(relocate(evmState(), 'kraken'), SOLANA_CHAIN);

    expect(state.txRef).toBe('');
    expect(state.address).toBe('');
  });

  it('should bring the transaction and address back on a return to an evm chain through a plain event', () => {
    const state = relocate(relocate(evmState(), 'kraken'), 'ethereum');

    expect(state).toMatchObject({ address: evmAddress, kind: HistoryEventEntryType.EVM_EVENT, txRef: evmTxRef });
  });

  it('should keep a solana address on a move from solana to an evm chain only if it is valid there', () => {
    const solana = filled(HistoryEventEntryType.SOLANA_EVENT, { address: solanaAddress, txRef: signature });

    expect(relocate(solana, 'ethereum')).toMatchObject({ address: '', kind: HistoryEventEntryType.EVM_EVENT, txRef: '' });
  });
});
