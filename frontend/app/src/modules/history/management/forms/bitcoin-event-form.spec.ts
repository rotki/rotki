import { describe, expect, it } from 'vitest';
import { bitcoinAssetFor, type BitcoinEventFormState, bitcoinEventSchema, emptyBitcoinEventForm, toBitcoinEventPayload } from '@/modules/history/management/forms/bitcoin-event-form';

const txId = '4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b';

const counterparties = (): string[] => ['bitcoin-core'];

function validState(): BitcoinEventFormState {
  return {
    ...emptyBitcoinEventForm('0'),
    amount: '1',
    eventSubtype: 'fee',
    eventType: 'spend',
    txRef: txId,
  };
}

/** Sorted, because the order zod reports issues in is not part of the contract. */
function issuePaths(state: BitcoinEventFormState): string[] {
  const result = bitcoinEventSchema(false, counterparties).safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.path.join('.')).sort();
}

describe('bitcoinAssetFor', () => {
  it('should follow the chain rather than let the asset be picked', () => {
    expect(bitcoinAssetFor('bitcoin')).toBe('BTC');
    expect(bitcoinAssetFor('bitcoin_cash')).toBe('BCH');
  });
});

describe('bitcoinEventSchema', () => {
  it('should accept a filled form', () => {
    expect(issuePaths(validState())).toEqual([]);
  });

  it('should not validate an asset, which the chain decides', () => {
    expect(issuePaths(emptyBitcoinEventForm('0'))).toEqual(['eventType', 'txRef']);
  });

  it('should reject a transaction id that is not a bitcoin one', () => {
    expect(issuePaths({ ...validState(), txRef: '0xnope' })).toEqual(['txRef']);
  });
});

describe('toBitcoinEventPayload', () => {
  it('should derive the asset from the location', () => {
    expect(toBitcoinEventPayload(validState()).asset).toBe('BTC');
    expect(toBitcoinEventPayload({ ...validState(), location: 'bitcoin_cash' }).asset).toBe('BCH');
  });

  it('should send a blank counterparty rather than null, which is what this endpoint wants', () => {
    expect(toBitcoinEventPayload(validState()).counterparty).toBe('');
  });

  it('should send null for a blank location label', () => {
    expect(toBitcoinEventPayload(validState()).locationLabel).toBeNull();
  });
});
