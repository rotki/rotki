/** Upper bound on sparkline points; a long, active history is subsampled to keep plotting cheap. */
export const SPARKLINE_MAX_POINTS = 120;

/**
 * Uniformly subsample `values` to at most `max` entries, always keeping the first and last so the
 * series still spans its full range (the last point is the event's "you are here" marker).
 */
export function downsample<T>(values: T[], max: number): T[] {
  if (values.length <= max)
    return values;

  const step = (values.length - 1) / (max - 1);
  const result: T[] = [];
  for (let i = 0; i < max; i++) {
    result.push(values[Math.round(i * step)]);
  }
  return result;
}
