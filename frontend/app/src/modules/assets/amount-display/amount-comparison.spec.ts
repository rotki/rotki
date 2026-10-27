import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { sameMagnitude, sharedDecimals, sharesSignificantDigit, splitSharedPrefix } from '@/modules/assets/amount-display/amount-comparison';

describe('sharedDecimals', () => {
  it('should take the largest decimal count among the amounts', () => {
    expect(sharedDecimals(bigNumberify('1.5'), bigNumberify('0.000123'), bigNumberify('7'))).toBe(6);
  });

  it('should be zero for whole numbers or no amounts', () => {
    expect(sharedDecimals(bigNumberify('3'))).toBe(0);
    expect(sharedDecimals()).toBe(0);
  });
});

describe('sameMagnitude', () => {
  it('should hold for same-signed amounts with the same number of integer digits', () => {
    expect(sameMagnitude(bigNumberify('5.3832'), bigNumberify('5.296366'))).toBe(true);
    expect(sameMagnitude(bigNumberify('0.1004'), bigNumberify('0.0904'))).toBe(true);
    expect(sameMagnitude(bigNumberify('-12.5'), bigNumberify('-99'))).toBe(true);
  });

  it('should fail for a different number of integer digits or a different sign', () => {
    expect(sameMagnitude(bigNumberify('12.5'), bigNumberify('1.25'))).toBe(false);
    expect(sameMagnitude(bigNumberify('-0.5'), bigNumberify('0.5'))).toBe(false);
  });
});

describe('sharesSignificantDigit', () => {
  it('should be true once the shared part reaches a non-zero digit', () => {
    expect(sharesSignificantDigit(splitSharedPrefix('0.100412135', '0.100411633'))).toBe(true);
    expect(sharesSignificantDigit(splitSharedPrefix('5.3832', '5.296366'))).toBe(true);
  });

  it('should be false when the values differ from their first significant digit', () => {
    expect(sharesSignificantDigit(splitSharedPrefix('0.1004', '0.0904'))).toBe(false);
    expect(sharesSignificantDigit(splitSharedPrefix('0.0000005', '0.0000004'))).toBe(false);
    expect(sharesSignificantDigit(splitSharedPrefix('-0.5', '0.5'))).toBe(false);
  });
});

describe('splitSharedPrefix', () => {
  it('should split at the first digit that differs', () => {
    expect(splitSharedPrefix('0.100412135185230566', '0.100411633744152674')).toEqual({
      rest: '2135185230566',
      shared: '0.10041',
    });
  });

  it('should keep separators in the shared part', () => {
    expect(splitSharedPrefix('1,234.5678', '1,234.5699')).toEqual({ rest: '78', shared: '1,234.56' });
  });

  it('should put an equal value entirely in the shared part', () => {
    expect(splitSharedPrefix('0.5', '0.5')).toEqual({ rest: '', shared: '0.5' });
  });

  it('should put a value that differs from the first character entirely in the rest', () => {
    expect(splitSharedPrefix('-0.5', '0.5')).toEqual({ rest: '-0.5', shared: '' });
  });

  it('should treat a value that runs past the other one as differing from there', () => {
    expect(splitSharedPrefix('0.512', '0.5')).toEqual({ rest: '12', shared: '0.5' });
  });
});
