import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import type { Collection } from '@/modules/core/common/collection';
import { bigNumberify, Zero } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { useEthValidatorUtils } from '@/modules/staking/eth/use-eth-validator-utils';

function validator(overrides: Partial<EthereumValidator> = {}): EthereumValidator {
  return {
    amount: bigNumberify(32),
    index: 1,
    publicKey: '0xabc',
    status: 'active',
    type: 'validator',
    value: bigNumberify(64000),
    ...overrides,
  };
}

function collection(overrides: Partial<Collection<EthereumValidator>> = {}): Collection<EthereumValidator> {
  return {
    data: [],
    found: 0,
    limit: 10,
    total: 0,
    ...overrides,
  };
}

describe('useEthValidatorUtils', () => {
  const { getColor, getOwnershipPercentage, useTotal, useTotalAmount } = useEthValidatorUtils();

  describe('getColor', () => {
    it.each([
      ['active', 'success'],
      ['consolidated', 'secondary'],
      ['exited', 'error'],
      ['exiting', 'warning'],
      ['pending', 'info'],
    ])('should map %s to %s', (status, color) => {
      expect(getColor(status)).toBe(color);
    });

    it('should return undefined for an unknown status', () => {
      expect(getColor('unknown')).toBeUndefined();
    });
  });

  describe('getOwnershipPercentage', () => {
    it('should return the ownership percentage when present', () => {
      expect(getOwnershipPercentage(validator({ ownershipPercentage: '42' }))).toBe('42');
    });

    it('should default to 100 when the ownership percentage is missing', () => {
      expect(getOwnershipPercentage(validator())).toBe('100');
    });

    it('should default to 100 when the ownership percentage is empty', () => {
      expect(getOwnershipPercentage(validator({ ownershipPercentage: '' }))).toBe('100');
    });
  });

  describe('useTotal', () => {
    it('should expose the collection total value', () => {
      const rows = ref(collection({ totalValue: bigNumberify(500) }));
      expect(get(useTotal(rows)).toNumber()).toBe(500);
    });

    it('should fall back to zero when there is no total value', () => {
      const rows = ref(collection());
      expect(get(useTotal(rows))).toStrictEqual(Zero);
    });
  });

  describe('useTotalAmount', () => {
    it('should expose the collection total amount', () => {
      const rows = ref(collection({ totalAmount: bigNumberify(64) }));
      expect(get(useTotalAmount(rows)).toNumber()).toBe(64);
    });

    it('should fall back to zero when there is no total amount', () => {
      const rows = ref(collection());
      expect(get(useTotalAmount(rows))).toStrictEqual(Zero);
    });
  });
});
