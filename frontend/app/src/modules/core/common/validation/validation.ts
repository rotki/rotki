/// <reference lib="es2022.intl" />
import type { BaseValidation } from '@vuelidate/core';

/**
 * Converts an object of vuelidate's BaseValidation to an array of
 * strings to be passed to the components error-messages
 *
 * @param validation BaseValidation
 * @return string[]
 */
export function toMessages(validation: BaseValidation): string[] {
  return validation.$errors.map(e => get(e.$message));
}

/**
 * Validates if the input is a single visual character
 * This includes regular characters (a, b, 1, etc.) and emojis (😊, 👩‍💻, etc.)
 *
 * @param value The string to validate
 * @return true if the value is visually a single character
 */
export function isSingleVisualCharacter(value: string): boolean {
  if (!value)
    return false;

  // Use Intl.Segmenter to properly count grapheme clusters (visual characters)
  // This handles emojis, combined characters, and other complex Unicode properly
  const segmenter = new Intl.Segmenter(undefined, { granularity: 'grapheme' });
  const segments = Array.from(segmenter.segment(value));

  // Should have exactly one grapheme cluster
  return segments.length === 1;
}
