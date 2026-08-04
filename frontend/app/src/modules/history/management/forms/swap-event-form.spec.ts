import type { SwapEvent } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { emptySwapForm, type SwapFormState, swapIdentifiers, swapSchema, swapStateFromEvents, toSwapEditPayload, toSwapPayload } from '@/modules/history/management/forms/swap-event-form';

const groupIdentifier = '24bf5c3b2031b1224d7f0e642fde058ac8316039969762b67981372229fe1a7f';

function validState(): SwapFormState {
  return {
    ...emptySwapForm(),
    location: 'binance',
    receiveAmount: '20',
    receiveAsset: 'USD',
    spendAmount: '0.01',
    spendAsset: 'ETH',
  };
}

/** Sorted, because the order zod reports issues in is not part of the contract. */
function issuePaths(state: SwapFormState): string[] {
  const result = swapSchema().safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.path.join('.')).sort();
}

function swapEvent(overrides: Partial<SwapEvent>): SwapEvent {
  const base = {
    amount: bigNumberify('0.01'),
    asset: 'ETH',
    autoNotes: '',
    entryType: HistoryEventEntryType.SWAP_EVENT,
    eventSubtype: 'spend',
    eventType: 'trade',
    extraData: null,
    groupIdentifier,
    identifier: 2737,
    location: 'binance',
    locationLabel: null,
    sequenceIndex: 0,
    timestamp: 1742901211000,
    userNotes: 'spend note',
  } satisfies SwapEvent;

  return { ...base, ...overrides };
}

const spendEvent = swapEvent({});
const receiveEvent = swapEvent({
  amount: bigNumberify('20'),
  asset: 'USD',
  eventSubtype: 'receive',
  identifier: 2738,
  userNotes: 'receive note',
});
const feeEvent = swapEvent({
  amount: bigNumberify('1'),
  asset: 'USD',
  eventSubtype: 'fee',
  identifier: 2739,
  userNotes: 'fee note',
});

describe('swapSchema', () => {
  it('should accept a minimally filled swap', () => {
    expect(issuePaths(validState())).toEqual([]);
  });

  it('should require a location and both sides of the swap', () => {
    expect(issuePaths(emptySwapForm())).toEqual(['location', 'receiveAsset', 'spendAsset']);
  });

  it('should require a fee row once the fee has been enabled', () => {
    expect(issuePaths({ ...validState(), hasFee: true })).toEqual(['fees']);
  });

  it('should validate the rows of an enabled fee by their dotted path', () => {
    const state = { ...validState(), fees: [{ amount: '', asset: '', userNotes: '' }], hasFee: true };

    expect(issuePaths(state)).toEqual(['fees.0.amount', 'fees.0.asset']);
  });

  it('should not validate the rows of a disabled fee', () => {
    const state = { ...validState(), fees: [{ amount: '', asset: '', userNotes: '' }] };

    expect(issuePaths(state)).toEqual([]);
  });
});

describe('swapStateFromEvents', () => {
  it('should put each fee note on the fee it belongs to', () => {
    const state = swapStateFromEvents([spendEvent, receiveEvent, feeEvent]);

    expect(state.spendNotes).toBe('spend note');
    expect(state.receiveNotes).toBe('receive note');
    expect(state.fees).toEqual([{ amount: '1', asset: 'USD', userNotes: 'fee note' }]);
    expect(state.hasFee).toBe(true);
  });

  it('should leave the fee disabled when the group has none', () => {
    const state = swapStateFromEvents([spendEvent, receiveEvent]);

    expect(state.hasFee).toBe(false);
    expect(state.fees).toEqual([]);
  });

  it('should refuse a group that is missing a side of the swap', () => {
    expect(() => swapStateFromEvents([spendEvent])).toThrow();
  });
});

describe('swapIdentifiers', () => {
  it('should order the identifiers as spend, receive, then the fees', () => {
    const fees = [feeEvent, swapEvent({ eventSubtype: 'fee', identifier: 2740 })];

    // Deliberately out of order, since the group arrives however the API returned it.
    expect(swapIdentifiers([fees[1], receiveEvent, fees[0], spendEvent]))
      .toEqual([2737, 2738, 2740, 2739]);
  });
});

describe('toSwapPayload', () => {
  it('should send no fees at all while the fee is disabled', () => {
    const state = { ...validState(), fees: [{ amount: '1', asset: 'USD', userNotes: 'note' }] };
    const payload = toSwapPayload(state, 'abcd');

    expect(payload.fees).toBeUndefined();
    expect(payload.userNotes).toEqual(['', '']);
  });

  it('should flatten the fee notes onto the end of the notes array', () => {
    const state: SwapFormState = {
      ...validState(),
      fees: [
        { amount: '1', asset: 'USD', userNotes: 'first fee' },
        { amount: '0.5', asset: 'BTC', userNotes: 'second fee' },
      ],
      hasFee: true,
      receiveNotes: 'receive',
      spendNotes: 'spend',
    };

    const payload = toSwapPayload(state, 'abcd');

    expect(payload.fees).toEqual([{ amount: '1', asset: 'USD' }, { amount: '0.5', asset: 'BTC' }]);
    expect(payload.userNotes).toEqual(['spend', 'receive', 'first fee', 'second fee']);
  });

  it('should carry the unique id it is given', () => {
    expect(toSwapPayload(validState(), 'generated').uniqueId).toBe('generated');
  });
});

describe('toSwapEditPayload', () => {
  it('should drop the creation-only unique id and address the group', () => {
    const payload = toSwapEditPayload(toSwapPayload(validState(), 'abcd'), [1, 2]);

    expect(payload).not.toHaveProperty('uniqueId');
    expect(payload.identifiers).toEqual([1, 2]);
    expect(payload.entryType).toBe(HistoryEventEntryType.SWAP_EVENT);
  });
});
