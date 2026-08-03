import type { EthBlockEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType, Zero } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { emptyEthBlockForm, type EthBlockFormState, ethBlockSchema, ethBlockStateFromEvent, ethBlockStateFromGroup, toEthBlockPayload } from '@/modules/history/management/forms/eth-block-event-form';

const feeRecipient = '0xA090e606E30bD747d4E6245a1517EbE430F0057e';

function validState(): EthBlockFormState {
  return {
    ...emptyEthBlockForm(),
    blockNumber: '444',
    feeRecipient,
    validatorIndex: '122',
  };
}

/** Sorted, because the order zod reports issues in is not part of the contract. */
function issuePaths(state: EthBlockFormState, editing = false): string[] {
  const result = ethBlockSchema(editing).safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.path.join('.')).sort();
}

function blockEvent(overrides: Partial<EthBlockEvent>): EthBlockEvent {
  const base = {
    amount: bigNumberify('100'),
    asset: 'ETH',
    blockNumber: 444,
    entryType: HistoryEventEntryType.ETH_BLOCK_EVENT,
    eventSubtype: 'block production',
    eventType: 'staking',
    groupIdentifier: 'BP1_444',
    identifier: 449,
    location: 'ethereum',
    locationLabel: feeRecipient,
    sequenceIndex: 0,
    timestamp: 1697588400000,
    validatorIndex: 122,
  } satisfies EthBlockEvent;

  return { ...base, ...overrides };
}

describe('ethBlockSchema', () => {
  it('should accept a filled form', () => {
    expect(issuePaths(validState())).toEqual([]);
  });

  it('should require the block number, fee recipient and validator index', () => {
    expect(issuePaths(emptyEthBlockForm())).toEqual(['blockNumber', 'feeRecipient', 'validatorIndex']);
  });

  it('should reject a fee recipient that is not an evm address', () => {
    expect(issuePaths({ ...validState(), feeRecipient: 'not-an-address' })).toEqual(['feeRecipient']);
  });

  it('should report a blank fee recipient as missing rather than as malformed', () => {
    expect(issuePaths({ ...validState(), feeRecipient: '' })).toEqual(['feeRecipient']);
  });

  it('should require a group identifier only while editing', () => {
    expect(issuePaths(validState())).toEqual([]);
    expect(issuePaths(validState(), true)).toEqual(['groupIdentifier']);
  });
});

describe('ethBlockStateFromEvent', () => {
  it('should read the mev reward flag off the event subtype', () => {
    expect(ethBlockStateFromEvent(blockEvent({})).isMevReward).toBe(false);
    expect(ethBlockStateFromEvent(blockEvent({ eventSubtype: 'mev reward' })).isMevReward).toBe(true);
  });

  it('should take the fee recipient from the location label', () => {
    expect(ethBlockStateFromEvent(blockEvent({})).feeRecipient).toBe(feeRecipient);
  });
});

describe('ethBlockStateFromGroup', () => {
  it('should carry over only what the group shares', () => {
    const state = ethBlockStateFromGroup(blockEvent({}));

    expect(state.blockNumber).toBe('444');
    expect(state.groupIdentifier).toBe('BP1_444');
    expect(state.validatorIndex).toBe('122');
    // The amount belongs to the event being added, not to the group.
    expect(state.amount).toBe('0');
  });
});

describe('toEthBlockPayload', () => {
  it('should send null rather than an empty group identifier', () => {
    expect(toEthBlockPayload(validState()).groupIdentifier).toBeNull();
  });

  it('should turn the numeric fields into numbers', () => {
    const payload = toEthBlockPayload(validState());

    expect(payload.blockNumber).toBe(444);
    expect(payload.validatorIndex).toBe(122);
  });

  it('should fall back to zero for an amount that is not a number', () => {
    expect(toEthBlockPayload({ ...validState(), amount: '' }).amount).toStrictEqual(Zero);
  });

  it('should not leak the presentation-only field', () => {
    expect(toEthBlockPayload(validState())).not.toHaveProperty('hasActualGroupIdentifier');
  });
});
