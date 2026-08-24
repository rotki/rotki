import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { isAmountExceeded, isTradeValid, maxSendableAmount } from '@/modules/wallet/send/trade-send-utils';

const VALID_ADDRESS = '0x9531C059098e3d194fF87FebB587aB07B30B1306';

describe('trade-send-utils', () => {
  describe('isAmountExceeded', () => {
    it('should allow an amount up to the max', () => {
      expect(isAmountExceeded('1', '2')).toBe(false);
      expect(isAmountExceeded('2', '2')).toBe(false);
    });

    it('should reject an amount above the max', () => {
      expect(isAmountExceeded('2.0000001', '2')).toBe(true);
    });

    it('should treat an unparsable amount as zero', () => {
      expect(isAmountExceeded('', '2')).toBe(false);
      expect(isAmountExceeded('not a number', '2')).toBe(false);
    });

    it('should treat an unparsable max as zero', () => {
      expect(isAmountExceeded('1', '')).toBe(true);
    });
  });

  describe('isTradeValid', () => {
    it('should accept a positive amount within the max to a valid address', () => {
      expect(isTradeValid('1', VALID_ADDRESS, '2')).toBe(true);
    });

    it('should reject a zero or empty amount', () => {
      expect(isTradeValid('0', VALID_ADDRESS, '2')).toBe(false);
      expect(isTradeValid('', VALID_ADDRESS, '2')).toBe(false);
    });

    it('should reject a missing or malformed recipient', () => {
      expect(isTradeValid('1', '', '2')).toBe(false);
      expect(isTradeValid('1', '0xnope', '2')).toBe(false);
    });

    it('should reject an amount over the max', () => {
      expect(isTradeValid('3', VALID_ADDRESS, '2')).toBe(false);
    });
  });

  describe('maxSendableAmount', () => {
    it('should leave the gas fee out of the sendable amount', () => {
      expect(maxSendableAmount(bigNumberify('2'), '0.5')).toBe('1.5');
    });

    it('should offer the whole balance when gas is free', () => {
      expect(maxSendableAmount(bigNumberify('2'), '0')).toBe('2');
    });

    it('should offer nothing when the balance is unknown', () => {
      expect(maxSendableAmount(undefined, '0.5')).toBe('0');
    });

    it('should go negative rather than lie when gas exceeds the balance', () => {
      expect(maxSendableAmount(bigNumberify('0.1'), '0.5')).toBe('-0.4');
    });
  });
});
