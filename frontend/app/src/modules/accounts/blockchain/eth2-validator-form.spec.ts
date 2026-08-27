import type { Eth2Validator } from '@/modules/balances/types/balances';
import { describe, expect, it } from 'vitest';
import { eth2ValidatorSchema, isValidOwnershipPercentage } from '@/modules/accounts/blockchain/eth2-validator-form';

const MESSAGES = {
  ownershipPercentage: 'ownership',
  required: 'required',
  validatorIndex: 'numeric',
};

const schema = eth2ValidatorSchema(MESSAGES);

/** Messages for one field, in the order the schema reports them. */
function messagesFor(value: Eth2Validator, field: keyof Eth2Validator): string[] {
  const result = schema.safeParse(value);
  if (result.success)
    return [];
  return result.error.issues.filter(issue => issue.path.join('.') === field).map(issue => issue.message);
}

describe('modules/accounts/blockchain/eth2-validator-form', () => {
  describe('isValidOwnershipPercentage', () => {
    it.each([
      ['', true],
      ['100', true],
      ['0.5', true],
      ['0', false],
      ['101', false],
      ['-1', false],
      ['abc', false],
    ])('should treat "%s" as %s', (value, valid) => {
      expect(isValidOwnershipPercentage(value)).toBe(valid);
    });
  });

  describe('the identifier pair', () => {
    it('should require an identifier when neither is given', () => {
      expect(messagesFor({}, 'validatorIndex')).toEqual([MESSAGES.required]);
      expect(messagesFor({}, 'publicKey')).toEqual([MESSAGES.required]);
    });

    it('should report a field the payload has not got yet as missing, not as mistyped, since it is bound to no message of its own', () => {
      expect(messagesFor({}, 'ownershipPercentage')).toEqual([]);
      expect(schema.safeParse({ validatorIndex: '42' }).success).toBe(true);
    });

    it.each([
      ['an index', { validatorIndex: '42' }],
      ['a public key', { publicKey: '0xabc' }],
      ['both', { publicKey: '0xabc', validatorIndex: '42' }],
    ])('should accept %s', (_label, value) => {
      expect(schema.safeParse(value).success).toBe(true);
    });

    it('should report a non-numeric index without also reporting it as missing', () => {
      expect(messagesFor({ validatorIndex: 'abc' }, 'validatorIndex')).toEqual([MESSAGES.validatorIndex]);
      expect(messagesFor({ validatorIndex: 'abc' }, 'publicKey')).toEqual([]);
    });

    it('should report both rules against a whitespace-only index, in rule order', () => {
      const value = { validatorIndex: ' ' };

      expect(messagesFor(value, 'validatorIndex')).toEqual([MESSAGES.validatorIndex, MESSAGES.required]);
      // The companion check reads the index as typed, so whitespace counts as filled for the key.
      expect(messagesFor(value, 'publicKey')).toEqual([]);
    });
  });

  describe('ownership percentage', () => {
    it('should reject a percentage outside the range even when the identifier is fine', () => {
      expect(messagesFor({ ownershipPercentage: '101', validatorIndex: '42' }, 'ownershipPercentage'))
        .toEqual([MESSAGES.ownershipPercentage]);
    });

    it('should report the identifier and the percentage together', () => {
      const value = { ownershipPercentage: '0' };

      expect(messagesFor(value, 'validatorIndex')).toEqual([MESSAGES.required]);
      expect(messagesFor(value, 'publicKey')).toEqual([MESSAGES.required]);
      expect(messagesFor(value, 'ownershipPercentage')).toEqual([MESSAGES.ownershipPercentage]);
    });
  });
});
