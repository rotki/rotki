import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { emptySubEvent, swapSubEventSchema, type SwapSubEventSource, toSubEventPayload, toSubEventState } from '@/modules/history/management/forms/swap/swap-sub-event';

function issuePaths(value: unknown, chain: 'evm' | 'solana' = 'evm'): string[] {
  const result = swapSubEventSchema(chain).safeParse(value);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.path.join('.'));
}

describe('swapSubEventSchema', () => {
  it('should require an amount and an asset', () => {
    expect(issuePaths(emptySubEvent())).toEqual(['amount', 'asset']);
  });

  it('should accept a row with only an amount and an asset', () => {
    expect(issuePaths({ ...emptySubEvent(), amount: '1', asset: 'ETH' })).toEqual([]);
  });

  it('should reject a location label that is not an address of the chain', () => {
    const row = { ...emptySubEvent(), amount: '1', asset: 'ETH', locationLabel: 'not-an-address' };

    expect(issuePaths(row)).toEqual(['locationLabel']);
  });

  it('should treat a blank location label as unset rather than invalid', () => {
    expect(issuePaths({ ...emptySubEvent(), amount: '1', asset: 'ETH' })).toEqual([]);
  });

  it('should validate the location label against the solana address format', () => {
    const row = {
      ...emptySubEvent(),
      amount: '1',
      asset: 'SOL',
      locationLabel: '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8',
    };

    expect(issuePaths(row, 'solana')).toEqual([]);
    // The same value is not a valid EVM address, so the EVM form must reject it.
    expect(issuePaths(row, 'evm')).toEqual(['locationLabel']);
  });
});

describe('toSubEventPayload', () => {
  it('should drop the optional fields that are blank', () => {
    const payload = toSubEventPayload({ ...emptySubEvent(), amount: '1', asset: 'ETH' });

    expect(payload).toEqual({ amount: '1', asset: 'ETH' });
  });

  it('should keep the optional fields that are set', () => {
    const payload = toSubEventPayload({
      amount: '1',
      asset: 'ETH',
      identifier: 42,
      locationLabel: '0x6e15887E2CEC81434C16D587709f64603b39b541',
      userNotes: 'a note',
    });

    expect(payload).toEqual({
      amount: '1',
      asset: 'ETH',
      identifier: 42,
      locationLabel: '0x6e15887E2CEC81434C16D587709f64603b39b541',
      userNotes: 'a note',
    });
  });

  it('should not send the price intent, which is form state rather than event data', () => {
    const payload = toSubEventPayload({
      ...emptySubEvent(),
      amount: '1',
      asset: 'ETH',
      priceIntent: { fromAsset: 'ETH', price: '2000', timestampMs: 1742901211000, toAsset: 'USD' },
    });

    expect(payload).not.toHaveProperty('priceIntent');
  });
});

describe('toSubEventState', () => {
  it('should turn the unset event fields into the empty strings an input binds to', () => {
    const event: SwapSubEventSource = {
      amount: bigNumberify('0.1'),
      asset: 'ETH',
      identifier: 3456,
      locationLabel: null,
      userNotes: undefined,
    };

    expect(toSubEventState(event)).toEqual({
      amount: '0.1',
      asset: 'ETH',
      identifier: 3456,
      locationLabel: '',
      userNotes: '',
    });
  });
});
