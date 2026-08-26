/// <reference lib="es2022.intl" />

/**
 * Whether the input is a single *visual* character.
 *
 * @remarks
 * Counts grapheme clusters, so an emoji built from several code points (👩‍💻) is one character, as is
 * an ordinary `a` or `1`. A plain `.length` check would not agree.
 */
export function isSingleVisualCharacter(value: string): boolean {
  if (!value)
    return false;

  const segmenter = new Intl.Segmenter(undefined, { granularity: 'grapheme' });
  const segments = Array.from(segmenter.segment(value));

  return segments.length === 1;
}
