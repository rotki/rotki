import { describe, expect, it } from 'vitest';
import { PasswordIssue } from '@/modules/auth/create-account/credentials/password-patterns';
import {
  PasswordStrength,
  ratePassword,
  strengthScore,
} from '@/modules/auth/create-account/credentials/password-strength';

describe('ratePassword', () => {
  describe('by length, when nothing is predictable', () => {
    it.each([
      ['', PasswordStrength.EMPTY],
      ['x', PasswordStrength.WEAK],
      ['G7k!pQz', PasswordStrength.WEAK],
      ['G7k!pQz9', PasswordStrength.FAIR],
      ['xK9#mQ2$vL7!', PasswordStrength.GOOD],
      ['sunflower meadow', PasswordStrength.STRONG],
      ['correct horse battery staple', PasswordStrength.STRONG],
    ])('should rate %j as %s', (password, expected) => {
      expect(ratePassword(password)).toStrictEqual({ strength: expected });
    });

    it('should count an emoji as one character, not its UTF-16 code units', () => {
      expect(ratePassword('🔒🐙🌵🎲').strength).toBe(PasswordStrength.WEAK);
    });
  });

  describe('predictable patterns', () => {
    it.each([
      ['password', PasswordIssue.COMMON_WORD],
      ['P@ssw0rd', PasswordIssue.COMMON_WORD],
      ['mybitcoin', PasswordIssue.COMMON_WORD],
      ['aaaaaaaaaaaaaaaaaaaa', PasswordIssue.REPEATS],
      ['kfqmkfqmkfqmkfqm', PasswordIssue.REPEATS],
      ['abcdefghijklmnopqr', PasswordIssue.SEQUENCE],
      ['zyxwvutsrqponmlkji', PasswordIssue.SEQUENCE],
      ['qwertyuiopasdfghjk', PasswordIssue.SEQUENCE],
    ])('should rate %j weak and name the %s pattern', (password, issue) => {
      expect(ratePassword(password)).toStrictEqual({ issue, strength: PasswordStrength.WEAK });
    });

    it('should still catch one repeated character past the length the block search covers', () => {
      expect(ratePassword('a'.repeat(80))).toStrictEqual({
        issue: PasswordIssue.REPEATS,
        strength: PasswordStrength.WEAK,
      });
    });

    it('should not count a long password as strong when it is mostly a pattern', () => {
      expect(ratePassword('sunshine12345678')).toStrictEqual({
        issue: PasswordIssue.COMMON_WORD,
        strength: PasswordStrength.WEAK,
      });
    });

    it('should report the profile name inside the password', () => {
      expect(ratePassword('xK9#kelsos#L7', 'Kelsos')).toStrictEqual({
        issue: PasswordIssue.CONTAINS_USERNAME,
        strength: PasswordStrength.FAIR,
      });
      expect(ratePassword('xK9#kelsos#L7')).toStrictEqual({ strength: PasswordStrength.GOOD });
    });

    it('should ignore a profile name too short to mean anything', () => {
      expect(ratePassword('xK9#mQ2$vL7!', 'mQ')).toStrictEqual({ strength: PasswordStrength.GOOD });
    });

    it('should rate digits alone one step lower than their length', () => {
      expect(ratePassword('8472910365829104')).toStrictEqual({
        issue: PasswordIssue.DIGITS_ONLY,
        strength: PasswordStrength.GOOD,
      });
    });

    it('should name no issue once the password is strong despite a pattern', () => {
      expect(ratePassword('purple elephant dancing abc')).toStrictEqual({ strength: PasswordStrength.STRONG });
    });
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
