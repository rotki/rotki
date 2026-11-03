import type { EthWithdrawalEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType, Zero } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import {
  emptyEthWithdrawalForm,
  type EthWithdrawalFormState,
  ethWithdrawalSchema,
  ethWithdrawalStateFromEvent,
  ethWithdrawalStateFromGroup,
  toEthWithdrawalPayload,
} from '@/modules/history/management/forms/eth-withdrawal-event-form';

const withdrawalAddress = '0xA090e606E30bD747d4E6245a1517EbE430F0057e';

function validState(): EthWithdrawalFormState {
  return {
    ...emptyEthWithdrawalForm(),
    amount: '0.05',
    validatorIndex: '122',
    withdrawalAddress,
  };
}

/** Sorted, because the order zod reports issues in is not part of the contract. */
function issuePaths(state: EthWithdrawalFormState, editing = false): string[] {
  const result = ethWithdrawalSchema(editing).safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.path.join('.')).sort();
}

function withdrawalEvent(overrides: Partial<EthWithdrawalEvent>): EthWithdrawalEvent {
  const base = {
    amount: bigNumberify('0.05'),
    asset: 'ETH',
    entryType: HistoryEventEntryType.ETH_WITHDRAWAL_EVENT,
    eventSubtype: 'remove asset',
    eventType: 'staking',
    groupIdentifier: 'EW_122_19000',
    identifier: 21,
    isExit: true,
    location: 'ethereum',
    locationLabel: withdrawalAddress,
    sequenceIndex: 0,
    timestamp: 1697588400000,
    validatorIndex: 122,
  } satisfies EthWithdrawalEvent;

  return { ...base, ...overrides };
}

describe('ethWithdrawalSchema', () => {
  it('should accept a filled form', () => {
    expect(issuePaths(validState())).toEqual([]);
  });

  it('should require the amount, validator index and withdrawal address', () => {
    expect(issuePaths({ ...emptyEthWithdrawalForm(), amount: '' })).toEqual(['amount', 'validatorIndex', 'withdrawalAddress']);
  });

  it('should reject a withdrawal address that is not an evm address', () => {
    expect(issuePaths({ ...validState(), withdrawalAddress: 'not-an-address' })).toEqual(['withdrawalAddress']);
  });

  it('should report a blank withdrawal address once, as missing rather than as malformed', () => {
    const result = ethWithdrawalSchema(false).safeParse({ ...validState(), withdrawalAddress: '' });

    expect(result.success).toBe(false);
    expect(result.error?.issues).toHaveLength(1);
    expect(result.error?.issues[0].message).toBe('transactions.events.form.withdrawal_address.validation.non_empty');
  });

  it('should require a group identifier only while editing', () => {
    expect(issuePaths(validState())).toEqual([]);
    expect(issuePaths(validState(), true)).toEqual(['groupIdentifier']);
  });
});

describe('ethWithdrawalStateFromEvent', () => {
  it('should take the withdrawal address from the location label', () => {
    expect(ethWithdrawalStateFromEvent(withdrawalEvent({})).withdrawalAddress).toBe(withdrawalAddress);
    expect(ethWithdrawalStateFromEvent(withdrawalEvent({ locationLabel: null })).withdrawalAddress).toBe('');
  });

  it.each([true, false])('should keep the exit flag at %s', (isExit) => {
    expect(ethWithdrawalStateFromEvent(withdrawalEvent({ isExit })).isExit).toBe(isExit);
  });

  it('should read the numbers as strings for the inputs', () => {
    const state = ethWithdrawalStateFromEvent(withdrawalEvent({}));

    expect(state.amount).toBe('0.05');
    expect(state.validatorIndex).toBe('122');
  });

  it('should show the linked group identifier when the event has one', () => {
    const state = ethWithdrawalStateFromEvent(withdrawalEvent({ actualGroupIdentifier: 'LINKED' }));

    expect(state.groupIdentifier).toBe('LINKED');
    expect(state.hasActualGroupIdentifier).toBe(true);
  });
});

describe('ethWithdrawalStateFromGroup', () => {
  it('should carry over only what the group shares', () => {
    const state = ethWithdrawalStateFromGroup(withdrawalEvent({}));

    expect(state.groupIdentifier).toBe('EW_122_19000');
    expect(state.timestamp).toBe(1697588400000);
    expect(state.validatorIndex).toBe('122');
    expect(state.withdrawalAddress).toBe(withdrawalAddress);
    expect(state.amount).toBe('0');
    expect(state.isExit).toBe(false);
  });
});

describe('toEthWithdrawalPayload', () => {
  it('should build the payload the backend takes', () => {
    expect(toEthWithdrawalPayload({ ...validState(), isExit: true, timestamp: 1697588400000 })).toEqual({
      amount: bigNumberify('0.05'),
      entryType: HistoryEventEntryType.ETH_WITHDRAWAL_EVENT,
      groupIdentifier: null,
      isExit: true,
      timestamp: 1697588400000,
      validatorIndex: 122,
      withdrawalAddress,
    });
  });

  it('should send the group identifier when there is one', () => {
    expect(toEthWithdrawalPayload({ ...validState(), groupIdentifier: 'EW_122_19000' }).groupIdentifier).toBe('EW_122_19000');
  });

  it('should fall back to zero for an amount that is not a number', () => {
    expect(toEthWithdrawalPayload({ ...validState(), amount: '' }).amount).toStrictEqual(Zero);
  });

  it('should not leak the presentation-only field or the price intent', () => {
    const payload = toEthWithdrawalPayload({
      ...validState(),
      priceIntent: { fromAsset: 'ETH', price: '1600', timestampMs: 1697588400000, toAsset: 'USD' },
    });

    expect(payload).not.toHaveProperty('hasActualGroupIdentifier');
    expect(payload).not.toHaveProperty('priceIntent');
  });
});
