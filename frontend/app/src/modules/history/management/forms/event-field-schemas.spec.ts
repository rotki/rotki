import { describe, expect, it } from 'vitest';
import {
  optionalEthAddress,
  requiredAmount,
  requiredEvmTxHash,
  requiredSolanaSignature,
  validCounterparty,
} from '@/modules/history/management/forms/event-field-schemas';

/** The first issue message, or undefined when the value parses. */
function firstIssue(schema: { safeParse: (value: unknown) => any }, value: unknown): string | undefined {
  const result = schema.safeParse(value);
  return result.success ? undefined : result.error.issues[0].message;
}

const VALID_TX_HASH = '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f';
const VALID_ADDRESS = '0xA090e606E30bD747d4E6245a1517EbE430F0057e';

describe('event field schemas', () => {
  describe('requiredAmount', () => {
    it('should reject an empty amount with the non-empty key', () => {
      expect(firstIssue(requiredAmount(), '')).toBe('transactions.events.form.amount.validation.non_empty');
    });

    it('should accept any non-empty amount', () => {
      expect(firstIssue(requiredAmount(), '0.1')).toBeUndefined();
    });
  });

  describe('optionalEthAddress', () => {
    it('should accept a blank address', () => {
      expect(firstIssue(optionalEthAddress(), '')).toBeUndefined();
    });

    it('should accept a valid address', () => {
      expect(firstIssue(optionalEthAddress(), VALID_ADDRESS)).toBeUndefined();
    });

    it('should reject a malformed address', () => {
      expect(firstIssue(optionalEthAddress(), '0xnope')).toBe('transactions.events.form.address.validation.valid');
    });
  });

  describe('requiredEvmTxHash', () => {
    it('should report only the non-empty key when blank', () => {
      const result = requiredEvmTxHash().safeParse('');
      expect(result.success).toBe(false);
      // The "valid" check tolerates blank on purpose, so an empty field does not report twice.
      expect(result.success ? [] : result.error.issues.map((issue: any) => issue.message)).toEqual([
        'transactions.events.form.tx_hash.validation.non_empty',
      ]);
    });

    it('should reject a malformed hash', () => {
      expect(firstIssue(requiredEvmTxHash(), '0x1234')).toBe('transactions.events.form.tx_hash.validation.valid');
    });

    it('should accept a valid hash', () => {
      expect(firstIssue(requiredEvmTxHash(), VALID_TX_HASH)).toBeUndefined();
    });
  });

  describe('requiredSolanaSignature', () => {
    it('should reject a blank signature', () => {
      expect(firstIssue(requiredSolanaSignature(), '')).toBe('transactions.events.form.signature.validation.non_empty');
    });

    it('should reject a malformed signature', () => {
      expect(firstIssue(requiredSolanaSignature(), 'not-a-signature')).toBe(
        'transactions.events.form.signature.validation.valid',
      );
    });
  });

  describe('validCounterparty', () => {
    it('should accept a blank counterparty', () => {
      expect(firstIssue(validCounterparty(() => ['uniswap-v3']), '')).toBeUndefined();
    });

    it('should accept a known counterparty', () => {
      expect(firstIssue(validCounterparty(() => ['uniswap-v3']), 'uniswap-v3')).toBeUndefined();
    });

    it('should accept an address as a counterparty', () => {
      expect(firstIssue(validCounterparty(() => []), VALID_ADDRESS)).toBeUndefined();
    });

    it('should reject an unknown non-address counterparty', () => {
      expect(firstIssue(validCounterparty(() => ['uniswap-v3']), 'nope')).toBe(
        'transactions.events.form.counterparty.validation.valid',
      );
    });

    it('should read the counterparty list at parse time, not at construction', () => {
      let known: string[] = [];
      const schema = validCounterparty(() => known);

      expect(firstIssue(schema, 'uniswap-v3')).toBeDefined();

      known = ['uniswap-v3'];

      expect(firstIssue(schema, 'uniswap-v3')).toBeUndefined();
    });
  });
});
