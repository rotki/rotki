import type { EvmSwapEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { emptyEvmSwapForm, type EvmSwapFormState, evmSwapSchema, evmSwapStateFromEvents, toEvmSwapPayload } from '@/modules/history/management/forms/evm-swap-event-form';

const txRef = '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f';
const address = '0xA090e606E30bD747d4E6245a1517EbE430F0057e';
const locationLabel = '0x6e15887E2CEC81434C16D587709f64603b39b541';

function validState(): EvmSwapFormState {
  return {
    ...emptyEvmSwapForm(),
    location: 'ethereum',
    receive: [{ amount: '300', asset: 'USDC', locationLabel: '', userNotes: '' }],
    spend: [{ amount: '0.1', asset: 'ETH', locationLabel: '', userNotes: '' }],
    txRef,
  };
}

/** Sorted, because the order zod reports issues in is not part of the contract. */
function issuePaths(state: EvmSwapFormState): string[] {
  const result = evmSwapSchema().safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.path.join('.')).sort();
}

function swapEvent(overrides: Partial<EvmSwapEvent>): EvmSwapEvent {
  const base = {
    address,
    amount: bigNumberify('0.1'),
    asset: 'ETH',
    autoNotes: '',
    counterparty: 'uniswap-v3',
    entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
    eventSubtype: 'spend',
    eventType: 'trade',
    extraData: null,
    groupIdentifier: `1${txRef}`,
    identifier: 3456,
    location: 'ethereum',
    locationLabel,
    sequenceIndex: 0,
    timestamp: 1742901211000,
    txRef,
    userNotes: 'spend note',
  } satisfies EvmSwapEvent;

  return { ...base, ...overrides };
}

describe('evmSwapSchema', () => {
  it('should accept a minimally filled swap', () => {
    expect(issuePaths(validState())).toEqual([]);
  });

  it('should require a location and a transaction hash', () => {
    expect(issuePaths(emptyEvmSwapForm())).toEqual([
      'location',
      'receive.0.amount',
      'receive.0.asset',
      'spend.0.amount',
      'spend.0.asset',
      'txRef',
    ]);
  });

  it('should key a row error by its dotted path so rows do not share messages', () => {
    const state = validState();
    state.spend.push({ amount: '', asset: '', locationLabel: '', userNotes: '' });

    expect(issuePaths(state)).toEqual(['spend.1.amount', 'spend.1.asset']);
  });

  it('should require a fee row only once the fee has been enabled', () => {
    const state = validState();
    expect(issuePaths(state)).toEqual([]);

    state.hasFee = true;

    expect(issuePaths(state)).toEqual(['fee']);
  });

  it('should not validate the rows of a disabled fee', () => {
    const state = validState();
    state.fee = [{ amount: '', asset: '', locationLabel: '', userNotes: '' }];

    // The rows are hidden while the fee is off, so an error on them would be unfixable.
    expect(issuePaths(state)).toEqual([]);
  });

  it('should validate the rows of an enabled fee by their dotted path', () => {
    const state = validState();
    state.hasFee = true;
    state.fee = [{ amount: '', asset: '', locationLabel: '', userNotes: '' }];

    expect(issuePaths(state)).toEqual(['fee.0.amount', 'fee.0.asset']);
  });

  it('should reject a transaction hash that is not an evm one', () => {
    expect(issuePaths({ ...validState(), txRef: '0xnope' })).toEqual(['txRef']);
  });

  it('should report a blank transaction hash as missing rather than as malformed', () => {
    expect(issuePaths({ ...validState(), txRef: '' })).toEqual(['txRef']);
  });
});

describe('evmSwapStateFromEvents', () => {
  it('should split a group into its spend, receive and fee rows', () => {
    const state = evmSwapStateFromEvents([
      swapEvent({}),
      swapEvent({ amount: bigNumberify('300'), asset: 'USDC', eventSubtype: 'receive', identifier: 3457 }),
      swapEvent({ amount: bigNumberify('0.005'), eventSubtype: 'fee', identifier: 3458 }),
    ]);

    expect(state.spend).toHaveLength(1);
    expect(state.receive).toEqual([{
      amount: '300',
      asset: 'USDC',
      identifier: 3457,
      locationLabel,
      userNotes: 'spend note',
    }]);
    expect(state.hasFee).toBe(true);
    expect(state.location).toBe('ethereum');
    expect(state.sequenceIndex).toBe('0');
  });

  it('should leave the fee disabled when the group has no fee event', () => {
    const state = evmSwapStateFromEvents([
      swapEvent({}),
      swapEvent({ eventSubtype: 'receive', identifier: 3457 }),
    ]);

    expect(state.hasFee).toBe(false);
    expect(state.fee).toEqual([]);
  });

  it('should refuse a group that is missing a side of the swap', () => {
    expect(() => evmSwapStateFromEvents([swapEvent({})])).toThrow();
  });
});

describe('toEvmSwapPayload', () => {
  it('should omit the fee entirely when it is disabled', () => {
    const state = validState();
    state.fee = [{ amount: '0.005', asset: 'ETH', locationLabel: '', userNotes: '' }];

    expect(toEvmSwapPayload(state)).not.toHaveProperty('fee');
  });

  it('should include the fee once it is enabled', () => {
    const state = validState();
    state.hasFee = true;
    state.fee = [{ amount: '0.005', asset: 'ETH', locationLabel: '', userNotes: '' }];

    expect(toEvmSwapPayload(state).fee).toEqual([{ amount: '0.005', asset: 'ETH' }]);
  });

  it('should omit a blank address rather than send an empty string', () => {
    expect(toEvmSwapPayload(validState())).not.toHaveProperty('address');
  });

  it('should not leak the hasFee toggle into the payload', () => {
    expect(toEvmSwapPayload(validState())).not.toHaveProperty('hasFee');
  });

  it('should carry the entry type the backend dispatches on', () => {
    expect(toEvmSwapPayload({ ...validState(), address }).address).toBe(address);
    expect(toEvmSwapPayload(validState()).entryType).toBe(HistoryEventEntryType.EVM_SWAP_EVENT);
  });
});
