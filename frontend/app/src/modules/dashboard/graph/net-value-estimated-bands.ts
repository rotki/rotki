/** A stretch of the chart drawn as estimated, unix seconds. */
export interface EstimatedBand {
  readonly start: number;
  readonly end: number;
}

function midpoint(a: number, b: number): number {
  return a + (b - a) / 2;
}

/**
 * The stretches of a series whose points are estimated, one band per run of estimated points.
 *
 * @remarks
 * A band reaches halfway to the neighbouring points on each side, so a single estimated point gets
 * a visible band and two adjacent runs never share an edge with an exact point.
 *
 * @param times - point times, unix seconds, ascending
 * @param estimated - per point, whether it is estimated; a missing entry counts as not
 */
export function estimatedBands(times: readonly number[], estimated: readonly boolean[] | undefined): EstimatedBand[] {
  if (!estimated)
    return [];
  const bands: EstimatedBand[] = [];
  let runStart: number | undefined;
  for (let index = 0; index < times.length; index++) {
    if (estimated[index]) {
      runStart ??= index;
      continue;
    }
    if (runStart !== undefined) {
      bands.push(bandOf(times, runStart, index - 1));
      runStart = undefined;
    }
  }
  if (runStart !== undefined)
    bands.push(bandOf(times, runStart, times.length - 1));
  return bands;
}

function bandOf(times: readonly number[], first: number, last: number): EstimatedBand {
  const before = times[first - 1];
  const after = times[last + 1];
  return {
    end: after === undefined ? times[last] : midpoint(times[last], after),
    start: before === undefined ? times[first] : midpoint(before, times[first]),
  };
}
