import { One } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { isRowValuePending, isTotalValuePending } from '@/modules/balances/value-pending';

const pending = (asset: string): boolean => asset.startsWith('PENDING');

describe('isRowValuePending', () => {
  it('should be pending when the row has no price yet', () => {
    expect(isRowValuePending({ asset: 'PENDING_ETH' }, pending)).toBe(true);
  });

  it('should not be pending when the row is priced', () => {
    expect(isRowValuePending({ asset: 'ETH' }, pending)).toBe(false);
  });

  it('should be pending when one member of a group is unpriced', () => {
    const row = {
      asset: 'USDC',
      breakdown: [
        { amount: One, asset: 'USDC', price: One, value: One },
        { amount: One, asset: 'PENDING_USDC_BASE', price: One, value: One },
      ],
    };

    expect(isRowValuePending(row, pending)).toBe(true);
  });

  it('should not be pending when every member of a group is priced', () => {
    const row = {
      asset: 'USDC',
      breakdown: [
        { amount: One, asset: 'USDC', price: One, value: One },
        { amount: One, asset: 'USDC_BASE', price: One, value: One },
      ],
    };

    expect(isRowValuePending(row, pending)).toBe(false);
  });
});

describe('isTotalValuePending', () => {
  it('should be pending when any row it sums is', () => {
    expect(isTotalValuePending([{ asset: 'ETH' }, { asset: 'PENDING_DAI' }], pending)).toBe(true);
  });

  it('should not be pending when every row is priced', () => {
    expect(isTotalValuePending([{ asset: 'ETH' }, { asset: 'DAI' }], pending)).toBe(false);
  });

  it('should not be pending with nothing to sum', () => {
    expect(isTotalValuePending([], pending)).toBe(false);
  });
});
