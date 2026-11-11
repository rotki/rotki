import { describe, expect, it } from 'vitest';
import {
  PasswordStrength,
  passwordStrength,
  strengthScore,
} from '@/modules/auth/create-account/credentials/password-strength';

describe('passwordStrength', () => {
  it.each([
    ['', PasswordStrength.EMPTY],
    ['a', PasswordStrength.WEAK],
    ['1234567', PasswordStrength.WEAK],
    ['12345678', PasswordStrength.FAIR],
    ['12345678901', PasswordStrength.FAIR],
    ['123456789012', PasswordStrength.GOOD],
    ['123456789012345', PasswordStrength.GOOD],
    ['1234567890123456', PasswordStrength.STRONG],
    ['correct horse battery staple', PasswordStrength.STRONG],
  ])('should rate %j as %s', (password, expected) => {
    expect(passwordStrength(password)).toBe(expected);
  });

  it('should count an emoji as one character, not its UTF-16 code units', () => {
    expect(passwordStrength('🔒🔒🔒🔒')).toBe(PasswordStrength.WEAK);
  });
});

describe('strengthScore', () => {
  it('should fill more segments for each stronger rating', () => {
    const scores = [
      PasswordStrength.EMPTY,
      PasswordStrength.WEAK,
      PasswordStrength.FAIR,
      PasswordStrength.GOOD,
      PasswordStrength.STRONG,
    ].map(strengthScore);

    expect(scores).toStrictEqual([0, 1, 2, 3, 4]);
  });
});
