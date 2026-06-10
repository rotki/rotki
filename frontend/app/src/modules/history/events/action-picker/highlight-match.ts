export interface HighlightSegment {
  readonly text: string;
  readonly matched: boolean;
}

/**
 * Splits a label into segments around the first case-insensitive occurrence of
 * `query`, so the matched portion can be visually emphasised in the picker rows.
 *
 * RuiAutoComplete filters on a normalised token (lower-cased, non-alphanumerics
 * stripped) that doesn't map back onto the visible label, so this performs a
 * best-effort literal match instead: when the trimmed query appears contiguously
 * in the label it is highlighted, otherwise the label is returned unsegmented
 * (the row is still shown — the library filter already decided it matches).
 */
export function splitHighlight(label: string, query: string): HighlightSegment[] {
  const trimmed = query.trim();
  if (!trimmed)
    return [{ matched: false, text: label }];

  const index = label.toLowerCase().indexOf(trimmed.toLowerCase());
  if (index === -1)
    return [{ matched: false, text: label }];

  const end = index + trimmed.length;
  const segments: HighlightSegment[] = [];

  if (index > 0)
    segments.push({ matched: false, text: label.slice(0, index) });

  segments.push({ matched: true, text: label.slice(index, end) });

  if (end < label.length)
    segments.push({ matched: false, text: label.slice(end) });

  return segments;
}
