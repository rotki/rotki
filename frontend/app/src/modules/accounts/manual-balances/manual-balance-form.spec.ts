import type { RawManualBalance } from '@/modules/balances/types/manual-balances';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import {
  type ManualBalanceFormState,
  manualBalanceSchema,
  toFormState,
  toPayload,
} from '@/modules/accounts/manual-balances/manual-balance-form';
import { BalanceType } from '@/modules/balances/types/balances';

const MESSAGES = {
  amount: 'amount',
  asset: 'asset',
  labelEmpty: 'label empty',
  labelExists: (label: string): string => `label ${label} exists`,
  location: 'location',
};

function balance(overrides: Partial<RawManualBalance> = {}): RawManualBalance {
  return {
    amount: bigNumberify(10),
    asset: 'ETH',
    balanceType: BalanceType.ASSET,
    label: 'my wallet',
    location: 'external',
    tags: null,
    ...overrides,
  };
}

function state(overrides: Partial<ManualBalanceFormState> = {}): ManualBalanceFormState {
  return {
    amount: '10',
    asset: 'ETH',
    balanceType: BalanceType.ASSET,
    label: 'my wallet',
    location: 'external',
    tags: [],
    ...overrides,
  };
}

function messagesFor(value: ManualBalanceFormState, field: string, editing = false, takenLabels: string[] = []): string[] {
  const result = manualBalanceSchema(MESSAGES, { editing, takenLabels }).safeParse(value);
  if (result.success)
    return [];
  return result.error.issues.filter(issue => issue.path.join('.') === field).map(issue => issue.message);
}

describe('modules/accounts/manual-balances/manual-balance-form', () => {
  describe('the round trip', () => {
    it.each([
      ['a filled balance', state()],
      ['a cleared amount', state({ amount: '' })],
      ['no tags', state({ tags: [] })],
      ['tags', state({ tags: ['tag'] })],
      ['a liability', state({ balanceType: BalanceType.LIABILITY })],
    ])('should read %s back exactly as it was written, since anything lost returns as an edit the user never made', (_label, value) => {
      expect(toFormState(toPayload(balance(), value))).toEqual(value);
    });

    it('should keep the fields the form does not edit', () => {
      const existing = { ...balance(), assetIsMissing: true, identifier: 7 };

      const result = toPayload(existing, state({ label: 'renamed' }));

      expect(result.identifier).toBe(7);
      expect(result.assetIsMissing).toBe(true);
      expect(result.label).toBe('renamed');
    });

    it('should edit a missing amount as an empty field', () => {
      expect(toFormState(balance({ amount: bigNumberify(Number.NaN) })).amount).toBe('');
    });

    it.each(['-', '1.2.3', '0,5', '1 000'])('should carry an amount of %s as not a number, rather than throw out of the parse', (typed) => {
      expect(toPayload(balance(), state({ amount: typed })).amount.isNaN()).toBe(true);
    });

    it('should offer no tags as an empty list', () => {
      expect(toFormState(balance({ tags: null })).tags).toEqual([]);
    });

    it('should store an empty tag list as none', () => {
      expect(toPayload(balance(), state({ tags: [] })).tags).toBeNull();
    });
  });

  describe('the schema', () => {
    it.each([
      ['amount', state({ amount: '' }), MESSAGES.amount],
      ['asset', state({ asset: '' }), MESSAGES.asset],
      ['location', state({ location: '' }), MESSAGES.location],
      ['label', state({ label: '' }), MESSAGES.labelEmpty],
    ])('should require %s', (field, value, message) => {
      expect(messagesFor(value, field)).toEqual([message]);
    });

    it.each([
      ['amount', state({ amount: '  ' }), MESSAGES.amount],
      ['asset', state({ asset: '  ' }), MESSAGES.asset],
      ['label', state({ label: '  ' }), MESSAGES.labelEmpty],
    ])('should treat a whitespace-only %s as missing', (field, value, message) => {
      expect(messagesFor(value, field)).toEqual([message]);
    });

    it('should accept a filled balance', () => {
      expect(manualBalanceSchema(MESSAGES, { editing: false, takenLabels: [] }).safeParse(state()).success).toBe(true);
    });

    it('should reject a label another balance already uses', () => {
      expect(messagesFor(state(), 'label', false, ['my wallet'])).toEqual([MESSAGES.labelExists('my wallet')]);
    });

    it('should let an edited balance keep a taken label', () => {
      expect(messagesFor(state(), 'label', true, ['my wallet'])).toEqual([]);
    });

    it('should report a taken label before reporting it as empty, which is the order the field renders them in', () => {
      expect(messagesFor(state({ label: '' }), 'label', false, [''])).toEqual([
        MESSAGES.labelExists(''),
        MESSAGES.labelEmpty,
      ]);
    });
  });
});
