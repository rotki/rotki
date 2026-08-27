import { describe, expect, it } from 'vitest';
import { NewDetectedTokenKind } from '@/modules/assets/detection/types';
import { NewlyDetectedFilterKeys, tokenKindOf } from '@/modules/assets/detection/use-newly-detected-filter';

describe('tokenKindOf', () => {
  it('should read the kind the pill narrowed to', () => {
    expect(tokenKindOf({ [NewlyDetectedFilterKeys.TOKEN_KIND]: NewDetectedTokenKind.SOLANA }))
      .toBe(NewDetectedTokenKind.SOLANA);
  });

  it('should read an absent pill as every kind, which is what getAllIdentifiers takes undefined for', () => {
    expect(tokenKindOf({})).toBeUndefined();
  });

  it('should read a kind it does not know as every kind', () => {
    expect(tokenKindOf({ [NewlyDetectedFilterKeys.TOKEN_KIND]: 'nonsense' })).toBeUndefined();
  });

  it('should take the first of a repeated value', () => {
    expect(tokenKindOf({ [NewlyDetectedFilterKeys.TOKEN_KIND]: [NewDetectedTokenKind.EVM] }))
      .toBe(NewDetectedTokenKind.EVM);
  });

  it('should read a boolean as every kind', () => {
    expect(tokenKindOf({ [NewlyDetectedFilterKeys.TOKEN_KIND]: true })).toBeUndefined();
  });
});
