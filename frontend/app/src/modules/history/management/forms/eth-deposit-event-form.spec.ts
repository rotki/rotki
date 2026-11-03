import type { EthDepositEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType, Zero } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import {
  emptyEthDepositForm,
  type EthDepositFormState,
  ethDepositSchema,
  ethDepositStateFromEvent,
  ethDepositStateFromGroup,
  toEthDepositPayload,
} from '@/modules/history/management/forms/eth-deposit-event-form';

const depositor = '0xA090e606E30bD747d4E6245a1517EbE430F0057e';

const txRef = '0x8f2b9d7d5c4f9e2b8a1d1e0f7c6b5a4938271605f4e3d2c1b0a9f8e7d6c5b4a3';

function validState(): EthDepositFormState {
  return {
    ...emptyEthDepositForm('0'),
    amount: '32',
    depositor,
    txRef,
    validatorIndex: '122',
  };
}

/** Sorted, because the order zod reports issues in is not part of the contract. */
function issuePaths(state: EthDepositFormState, editing = false): string[] {
  const result = ethDepositSchema(editing).safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.path.join('.')).sort();
}

function depositEvent(overrides: Partial<EthDepositEvent>): EthDepositEvent {
  const base = {
    address: null,
    amount: bigNumberify('32'),
    asset: 'ETH',
    counterparty: 'eth2',
    entryType: HistoryEventEntryType.ETH_DEPOSIT_EVENT,
    eventSubtype: 'deposit asset',
    eventType: 'staking',
    extraData: { note: 'kept' },
    groupIdentifier: 'DEPOSIT_1',
    identifier: 12,
    location: 'ethereum',
    locationLabel: depositor,
    sequenceIndex: 3,
    timestamp: 1697588400000,
    txRef,
    validatorIndex: 122,
  } satisfies EthDepositEvent;

  return { ...base, ...overrides };
}

describe('ethDepositSchema', () => {
  it('should accept a filled form', () => {
    expect(issuePaths(validState())).toEqual([]);
  });

  it('should require the amount, depositor, transaction hash and validator index', () => {
    expect(issuePaths({ ...emptyEthDepositForm('0'), amount: '' })).toEqual(['amount', 'depositor', 'txRef', 'validatorIndex']);
  });

  it('should require a sequence index', () => {
    expect(issuePaths({ ...validState(), sequenceIndex: '' })).toEqual(['sequenceIndex']);
  });

  it.each([
    { field: 'depositor', value: 'not-an-address' },
    { field: 'txRef', value: '0x1234' },
  ] satisfies { field: keyof EthDepositFormState; value: string }[])('should reject a malformed $field', ({ field, value }) => {
    expect(issuePaths({ ...validState(), [field]: value })).toEqual([field]);
  });

  it('should report a blank depositor once, as missing rather than as malformed', () => {
    const result = ethDepositSchema(false).safeParse({ ...validState(), depositor: '' });

    expect(result.success).toBe(false);
    expect(result.error?.issues).toHaveLength(1);
    expect(result.error?.issues[0].message).toBe('transactions.events.form.depositor.validation.non_empty');
  });

  it('should require a group identifier only while editing', () => {
    expect(issuePaths(validState())).toEqual([]);
    expect(issuePaths(validState(), true)).toEqual(['groupIdentifier']);
  });
});

describe('emptyEthDepositForm', () => {
  it('should start on the sequence index the dialog suggests, or zero without one', () => {
    expect(emptyEthDepositForm('4').sequenceIndex).toBe('4');
    expect(emptyEthDepositForm('').sequenceIndex).toBe('0');
  });
});

describe('ethDepositStateFromEvent', () => {
  it('should take the depositor from the location label', () => {
    expect(ethDepositStateFromEvent(depositEvent({})).depositor).toBe(depositor);
    expect(ethDepositStateFromEvent(depositEvent({ locationLabel: null })).depositor).toBe('');
  });

  it('should carry the extra data through, and start an event without any on an empty object', () => {
    expect(ethDepositStateFromEvent(depositEvent({})).extraData).toEqual({ note: 'kept' });
    expect(ethDepositStateFromEvent(depositEvent({ extraData: null })).extraData).toEqual({});
  });

  it('should read the numbers as strings for the inputs', () => {
    const state = ethDepositStateFromEvent(depositEvent({ amount: bigNumberify('32.5') }));

    expect(state.amount).toBe('32.5');
    expect(state.sequenceIndex).toBe('3');
    expect(state.validatorIndex).toBe('122');
  });

  it('should show the linked group identifier when the event has one', () => {
    const state = ethDepositStateFromEvent(depositEvent({ actualGroupIdentifier: 'LINKED' }));

    expect(state.groupIdentifier).toBe('LINKED');
    expect(state.hasActualGroupIdentifier).toBe(true);
  });
});

describe('ethDepositStateFromGroup', () => {
  it('should carry over only what the group shares', () => {
    const state = ethDepositStateFromGroup(depositEvent({}), '5');

    expect(state.depositor).toBe(depositor);
    expect(state.groupIdentifier).toBe('DEPOSIT_1');
    expect(state.timestamp).toBe(1697588400000);
    expect(state.txRef).toBe(txRef);
    expect(state.validatorIndex).toBe('122');
    expect(state.sequenceIndex).toBe('5');
    expect(state.amount).toBe('0');
    expect(state.extraData).toEqual({});
  });
});

describe('toEthDepositPayload', () => {
  it('should build the payload the backend takes', () => {
    expect(toEthDepositPayload({ ...validState(), extraData: { note: 'kept' }, timestamp: 1697588400000 })).toEqual({
      amount: bigNumberify('32'),
      depositor,
      entryType: HistoryEventEntryType.ETH_DEPOSIT_EVENT,
      extraData: { note: 'kept' },
      groupIdentifier: null,
      sequenceIndex: '0',
      timestamp: 1697588400000,
      txRef,
      validatorIndex: 122,
    });
  });

  it('should send the group identifier when there is one', () => {
    expect(toEthDepositPayload({ ...validState(), groupIdentifier: 'DEPOSIT_1' }).groupIdentifier).toBe('DEPOSIT_1');
  });

  it('should fall back to sequence index zero when it is blank', () => {
    expect(toEthDepositPayload({ ...validState(), sequenceIndex: '' }).sequenceIndex).toBe('0');
  });

  it('should fall back to zero for an amount that is not a number', () => {
    expect(toEthDepositPayload({ ...validState(), amount: '' }).amount).toStrictEqual(Zero);
  });

  it('should not leak the presentation-only field or the price intent', () => {
    const payload = toEthDepositPayload({ ...validState(), priceIntent: { fromAsset: 'ETH', price: '1600', timestampMs: 1697588400000, toAsset: 'USD' } });

    expect(payload).not.toHaveProperty('hasActualGroupIdentifier');
    expect(payload).not.toHaveProperty('priceIntent');
  });
});
