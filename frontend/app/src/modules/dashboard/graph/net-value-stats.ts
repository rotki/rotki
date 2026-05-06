import { type BigNumber, Zero } from '@rotki/common';

export interface NetValueZoomRange {
  /** Inclusive start timestamp in seconds. */
  start: number;
  /** Inclusive end timestamp in seconds. */
  end: number;
}

export interface NetValueDeltaResult {
  startingValue: BigNumber;
  endValue: BigNumber;
  balanceDelta: BigNumber;
}

function firstNonZero(data: BigNumber[], from: number, to: number): BigNumber {
  // Skip leading zeros — a fresh portfolio reports zero before its first snapshot.
  let start = data[from];
  if (!start)
    return Zero;
  if (start.isZero()) {
    for (let i = from + 1; i <= to; i++) {
      if (data[i]?.gt(0)) {
        start = data[i];
        break;
      }
    }
  }
  return start;
}

interface IndexRange {
  first: number;
  last: number;
}

function findWindowIndices(times: number[], zoom: NetValueZoomRange): IndexRange {
  let first = -1;
  let last = -1;
  for (const [i, t] of times.entries()) {
    if (t < zoom.start || t > zoom.end)
      continue;
    if (first === -1)
      first = i;
    last = i;
  }
  return { first, last };
}

function isFullRange(times: number[], zoom: NetValueZoomRange | undefined): boolean {
  if (!zoom)
    return true;
  const last = times.at(-1);
  return last !== undefined && zoom.start <= times[0] && zoom.end >= last;
}

/**
 * Without a zoom (or when zoom covers the full range) returns the legacy
 * delta: first non-zero datapoint vs live `totalNetWorth`. With a partial
 * zoom, both ends come from the visible window.
 */
export function computeNetValueDelta(
  data: BigNumber[],
  times: number[],
  totalNetWorth: BigNumber,
  zoom?: NetValueZoomRange,
): NetValueDeltaResult {
  if (data.length === 0 || times.length === 0) {
    return { balanceDelta: Zero, endValue: Zero, startingValue: Zero };
  }

  if (!zoom || isFullRange(times, zoom)) {
    const startingValue = firstNonZero(data, 0, data.length - 1);
    const balanceDelta = totalNetWorth.minus(startingValue);
    return { balanceDelta, endValue: totalNetWorth, startingValue };
  }

  const { first, last } = findWindowIndices(times, zoom);
  if (first === -1) {
    return { balanceDelta: Zero, endValue: Zero, startingValue: Zero };
  }

  const startingValue = firstNonZero(data, first, last);
  const endValue = data[last] ?? Zero;
  const balanceDelta = endValue.minus(startingValue);
  return { balanceDelta, endValue, startingValue };
}
