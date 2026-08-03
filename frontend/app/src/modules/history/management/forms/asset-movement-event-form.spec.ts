import type { AssetMovementEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType, Zero } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { type AssetMovementFormState, assetMovementSchema, assetMovementStateFromEvents, emptyAssetMovementForm, toAssetMovementEditPayload, toAssetMovementPayload } from '@/modules/history/management/forms/asset-movement-event-form';

function validState(): AssetMovementFormState {
  return {
    ...emptyAssetMovementForm('kraken'),
    amount: '10',
    asset: 'ETH',
  };
}

/** Sorted, because the order zod reports issues in is not part of the contract. */
function issuePaths(state: AssetMovementFormState): string[] {
  const result = assetMovementSchema().safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.path.join('.')).sort();
}

function movementEvent(overrides: Partial<AssetMovementEvent>): AssetMovementEvent {
  const base = {
    amount: bigNumberify(10),
    asset: 'ETH',
    entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
    eventSubtype: 'spend',
    eventType: 'withdrawal',
    extraData: {
      blockchain: 'optimism',
      reference: 'TEST123',
      transactionId: '0x9834594deca004e626ea06c287abab60003f3752402a2b09ca88657db50292cf',
    },
    groupIdentifier: 'STJ6KRHJYGA',
    identifier: 449,
    location: 'kraken',
    locationLabel: 'Kraken 1',
    sequenceIndex: 0,
    timestamp: 1696741486185,
    userNotes: 'History event notes',
  } satisfies AssetMovementEvent;

  return { ...base, ...overrides };
}

const entry = movementEvent({});
const feeEvent = movementEvent({
  amount: bigNumberify(0.1),
  eventSubtype: 'fee',
  identifier: 450,
  userNotes: 'fee note',
});

describe('assetMovementSchema', () => {
  it('should accept a movement with an asset and an amount', () => {
    expect(issuePaths(validState())).toEqual([]);
  });

  it('should require an asset and a location', () => {
    expect(issuePaths(emptyAssetMovementForm(''))).toEqual(['asset', 'location']);
  });

  it('should accept an enabled fee that is entirely blank', () => {
    // Which is how the form has always let a movement have no fee while the checkbox is on.
    expect(issuePaths({ ...validState(), hasFee: true })).toEqual([]);
  });

  it('should require the amount once the fee asset is filled in', () => {
    expect(issuePaths({ ...validState(), feeAsset: 'ETH', hasFee: true })).toEqual(['fee']);
  });

  it('should require the asset once the fee amount is filled in', () => {
    expect(issuePaths({ ...validState(), fee: '0.1', hasFee: true })).toEqual(['feeAsset']);
  });

  it('should not require either half while the fee is disabled', () => {
    expect(issuePaths({ ...validState(), fee: '0.1' })).toEqual([]);
  });
});

describe('assetMovementStateFromEvents', () => {
  it('should read the fee off the sibling event', () => {
    const state = assetMovementStateFromEvents([entry, feeEvent]);

    expect(state.hasFee).toBe(true);
    expect(state.fee).toBe('0.1');
    expect(state.feeAsset).toBe('ETH');
    expect(state.feeNotes).toBe('fee note');
  });

  it('should leave the fee off when the group has no fee event', () => {
    const state = assetMovementStateFromEvents([entry]);

    expect(state.hasFee).toBe(false);
    expect(state.fee).toBe('');
  });

  it('should unpack the extra data into its own fields', () => {
    const state = assetMovementStateFromEvents([entry]);

    expect(state.blockchain).toBe('optimism');
    expect(state.uniqueId).toBe('TEST123');
    expect(state.transactionId).toBe(entry.extraData?.transactionId);
  });

  it('should prefer a linked group identifier and mark it uneditable', () => {
    const linked = movementEvent({ actualGroupIdentifier: 'ACTUAL123' });
    const state = assetMovementStateFromEvents([linked]);

    expect(state.groupIdentifier).toBe('ACTUAL123');
    expect(state.hasActualGroupIdentifier).toBe(true);
  });
});

describe('toAssetMovementPayload', () => {
  it('should send no fee at all while the fee is disabled', () => {
    const state = { ...validState(), fee: '0.1', feeAsset: 'ETH' };
    const payload = toAssetMovementPayload(state, 'abcd');

    expect(payload.fee).toBeNull();
    expect(payload.feeAsset).toBeNull();
    expect(payload.userNotes).toEqual(['']);
  });

  it('should append the fee note to the notes once the fee is on', () => {
    const state: AssetMovementFormState = {
      ...validState(),
      fee: '0.1',
      feeAsset: 'ETH',
      feeNotes: 'fee note',
      hasFee: true,
      notes: 'movement note',
    };

    const payload = toAssetMovementPayload(state, 'abcd');

    expect(payload.fee).toBe('0.1');
    expect(payload.userNotes).toEqual(['movement note', 'fee note']);
  });

  it('should fall back to zero for an amount that is not a number', () => {
    expect(toAssetMovementPayload({ ...validState(), amount: '' }, 'abcd').amount).toStrictEqual(Zero);
  });

  it('should not leak the presentation-only fields', () => {
    const payload = toAssetMovementPayload(validState(), 'abcd');

    expect(payload).not.toHaveProperty('hasFee');
    expect(payload).not.toHaveProperty('hasActualGroupIdentifier');
    expect(payload).not.toHaveProperty('feeNotes');
  });
});

describe('toAssetMovementEditPayload', () => {
  it('should address the movement through the first of its identifiers', () => {
    const payload = toAssetMovementEditPayload(toAssetMovementPayload(validState(), 'abcd'), [449, 450]);

    expect(payload.identifier).toBe(449);
  });

  it('should refuse to build an edit payload with nothing to address', () => {
    expect(() => toAssetMovementEditPayload(toAssetMovementPayload(validState(), 'abcd'), [])).toThrow();
  });
});
