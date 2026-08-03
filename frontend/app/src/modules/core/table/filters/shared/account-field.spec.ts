import { describe, expect, it } from 'vitest';
import { type AccountFieldOptions, toAccountField } from '@/modules/core/table/filters/shared/account-field';

const accounts: AccountFieldOptions = {
  resolveCaption: (address: string): string | undefined => (address === '0xaaa' ? 'short:0xaaa' : undefined),
  resolveKeywords: (address: string): string => `${address} name`,
  resolveLabel: (address: string): string => (address === '0xaaa' ? 'Main' : `short:${address}`),
  resolveLoading: (address: string): boolean => address === '0xbbb',
  suggest: (): string[] => ['0xaaa', '0xbbb'],
};

describe('toAccountField', () => {
  it('should bind to the param the table asks for', () => {
    const field = toAccountField({ label: 'Account', paramKey: 'locationLabels', to: 'request' }, accounts);
    expect(field).toMatchObject({
      binding: { kind: 'param', paramKey: 'locationLabels', to: 'request' },
      display: 'account',
      key: 'account',
      label: 'Account',
      multiple: true,
    });
  });

  it('should always be multi-valued whichever table it is built for', () => {
    const field = toAccountField({ label: 'Account', paramKey: 'addresses', to: 'both' }, accounts);
    expect(field.multiple).toBe(true);
    expect(field.binding).toStrictEqual({ kind: 'param', paramKey: 'addresses', to: 'both' });
  });

  it('should resolve each value through the account list it was given', () => {
    const field = toAccountField({ label: 'Account', paramKey: 'addresses', to: 'both' }, accounts);
    expect(field.suggest?.()).toStrictEqual(['0xaaa', '0xbbb']);
    expect(field.resolveLabel?.('0xaaa')).toBe('Main');
    expect(field.resolveCaption?.('0xaaa')).toBe('short:0xaaa');
    expect(field.resolveCaption?.('0xbbb')).toBeUndefined();
    expect(field.resolveKeywords?.('0xaaa')).toBe('0xaaa name');
    expect(field.resolveLoading?.('0xbbb')).toBe(true);
  });

  describe('fromLegacy', () => {
    const field = toAccountField({ label: 'Account', paramKey: 'addresses', to: 'both' }, accounts);

    it('should take the address out of the old `label (address)` suggestion', () => {
      expect(field.fromLegacy?.('Main (0xaaa)')).toBe('0xaaa');
    });

    it('should keep a bare address, which is what a nameless account was stored as', () => {
      expect(field.fromLegacy?.('0xaaa')).toBe('0xaaa');
    });

    it('should take the trailing address when the label itself has brackets', () => {
      expect(field.fromLegacy?.('Main (cold) (0xaaa)')).toBe('0xaaa');
    });

    it('should keep a value it cannot read rather than dropping the filter', () => {
      expect(field.fromLegacy?.('Main (')).toBe('Main (');
    });
  });

  it('should offer only the is operator, since a param cannot express exclusion', () => {
    const field = toAccountField({ label: 'Account', paramKey: 'addresses', to: 'both' }, accounts);
    expect(field.operators).toStrictEqual(['is']);
    expect(field.allowExclusion).toBe(false);
  });
});
