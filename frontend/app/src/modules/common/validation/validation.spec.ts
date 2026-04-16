import { describe, expect, it } from 'vitest';
import { isSingleVisualCharacter } from './validation';

describe('isSingleVisualCharacter', () => {
  it('should return true for single regular characters', () => {
    expect(isSingleVisualCharacter('a')).toBe(true);
    expect(isSingleVisualCharacter('b')).toBe(true);
    expect(isSingleVisualCharacter('1')).toBe(true);
    expect(isSingleVisualCharacter('.')).toBe(true);
    expect(isSingleVisualCharacter(',')).toBe(true);
    expect(isSingleVisualCharacter(' ')).toBe(true); // space character
    expect(isSingleVisualCharacter('_')).toBe(true);
    expect(isSingleVisualCharacter('-')).toBe(true);
  });

  it('should return true for single emojis', () => {
    expect(isSingleVisualCharacter('😊')).toBe(true);
    expect(isSingleVisualCharacter('🎉')).toBe(true);
    expect(isSingleVisualCharacter('💰')).toBe(true);
    expect(isSingleVisualCharacter('⚡')).toBe(true);
  });

  it('should return true for complex emojis that appear as single visual character', () => {
    expect(isSingleVisualCharacter('👩‍💻')).toBe(true); // Woman technologist (multi-codepoint)
    expect(isSingleVisualCharacter('👨‍👩‍👧‍👦')).toBe(true); // Family emoji (multi-codepoint)
    expect(isSingleVisualCharacter('🏳️‍🌈')).toBe(true); // Rainbow flag (multi-codepoint)
    expect(isSingleVisualCharacter('👍🏻')).toBe(true); // Thumbs up with skin tone
  });

  it('should return false for multiple characters', () => {
    expect(isSingleVisualCharacter('ab')).toBe(false);
    expect(isSingleVisualCharacter('12')).toBe(false);
    expect(isSingleVisualCharacter('...')).toBe(false);
    expect(isSingleVisualCharacter('😊😊')).toBe(false);
    expect(isSingleVisualCharacter('a😊')).toBe(false);
  });

  it('should return false for empty or invalid values', () => {
    expect(isSingleVisualCharacter('')).toBe(false);
    // @ts-expect-error testing invalid input
    expect(isSingleVisualCharacter(null)).toBe(false);
    // @ts-expect-error testing invalid input
    expect(isSingleVisualCharacter(undefined)).toBe(false);
  });
});
