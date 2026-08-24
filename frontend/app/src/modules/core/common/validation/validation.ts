/// <reference lib="es2022.intl" />

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
