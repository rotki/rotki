import type { BigNumber } from '@rotki/common';
import { DAY_SECONDS, type KnownPrice } from '@/modules/statistics/pricing/price-series';

/** Evenly spaced points fetched per asset before any gap is refined, both range ends included. */
export const ANCHOR_COUNT = 8;

/** Gaps scoring below this are not worth a request. */
const SCORE_FLOOR = 1e-4;

/** An asset whose value stays below this share of the total is never fetched. */
const NEGLIGIBLE_SHARE = 0.001;

/**
 * The price move assumed across a gap with a failed end, where no ratio can be measured.
 *
 * @remarks
 * Moderate on purpose: such a gap is refined, but after gaps whose ends show a real move.
 */
const UNKNOWN_MOVE = 0.05;

/** Ranges up to this long are refined to daily prices, longer ones to weekly. */
const DAILY_RANGE_LIMIT = 92 * DAY_SECONDS;

export interface BackfillAsset {
  readonly asset: string;
  /** Prices of the asset in the main currency already cached. */
  readonly known: readonly KnownPrice[];
  /** Times the backend reported as having no price; never asked again. */
  readonly failed: readonly number[];
  /** The largest value held over the range, in the main currency. */
  readonly heldValue: BigNumber;
}

export interface BackfillRange {
  /** Unix seconds. */
  readonly start: number;
  /** Unix seconds. */
  readonly end: number;
}

/**
 * One request for `/balances/historical/asset/prices`: the backend prices
 * `fromTimestamp + i * interval` up to `toTimestamp`, skipping `excludeTimestamps`.
 */
export interface BackfillRequest {
  readonly asset: string;
  readonly fromTimestamp: number;
  readonly toTimestamp: number;
  readonly interval: number;
  readonly excludeTimestamps: number[];
  readonly kind: 'anchor' | 'refine';
  readonly score: number;
}

interface Probe {
  readonly time: number;
  readonly price: BigNumber | undefined;
}

/** The finest spacing worth fetching for a range: one chart sample. */
export function sampleInterval(range: BackfillRange): number {
  return range.end - range.start <= DAILY_RANGE_LIMIT ? DAY_SECONDS : 7 * DAY_SECONDS;
}

function anchorInterval(range: BackfillRange): number {
  return Math.max(1, Math.floor((range.end - range.start) / (ANCHOR_COUNT - 1)));
}

/** Known and failed times within half a day of the range, in time order. */
function probesOf(entry: BackfillAsset, range: BackfillRange): Probe[] {
  const margin = DAY_SECONDS / 2;
  const inside = (time: number): boolean => time >= range.start - margin && time <= range.end + margin;
  return [
    ...entry.known.filter(point => inside(point.time)).map(point => ({ price: point.price, time: point.time })),
    ...entry.failed.filter(inside).map(time => ({ price: undefined, time })),
  ].sort((a, b) => a.time - b.time);
}

function isCovered(probes: readonly Probe[], time: number, tolerance: number): boolean {
  return probes.some(probe => Math.abs(probe.time - time) <= tolerance);
}

/** A range under a day is one point: its start, asked for on its own. */
function pointRequest(entry: BackfillAsset, range: BackfillRange, probes: readonly Probe[]): BackfillRequest | undefined {
  if (isCovered(probes, range.start, DAY_SECONDS / 2))
    return undefined;
  return {
    asset: entry.asset,
    excludeTimestamps: [],
    fromTimestamp: range.start,
    interval: DAY_SECONDS,
    kind: 'anchor',
    score: Number.POSITIVE_INFINITY,
    toTimestamp: range.start,
  };
}

function anchorRequest(entry: BackfillAsset, range: BackfillRange, probes: readonly Probe[]): BackfillRequest | undefined {
  if (range.end - range.start < DAY_SECONDS)
    return pointRequest(entry, range, probes);
  const interval = anchorInterval(range);
  const tolerance = Math.max(DAY_SECONDS / 2, interval / 2);
  const anchors = Array.from({ length: ANCHOR_COUNT }, (_, index) => range.start + index * interval);
  const covered = anchors.filter(time => isCovered(probes, time, tolerance));
  if (covered.length === anchors.length)
    return undefined;
  return {
    asset: entry.asset,
    excludeTimestamps: covered,
    fromTimestamp: range.start,
    interval,
    kind: 'anchor',
    score: Number.POSITIVE_INFINITY,
    toTimestamp: range.start + (ANCHOR_COUNT - 1) * interval,
  };
}

function move(left: Probe, right: Probe): number {
  if (!left.price || !right.price || left.price.lte(0) || right.price.lte(0))
    return UNKNOWN_MOVE;
  return Math.abs(Math.log(right.price.dividedBy(left.price).toNumber()));
}

/**
 * The gap of an asset most worth splitting, as a request for its midpoint.
 *
 * @remarks
 * Score is held share × price move across the gap × gap length as a share of the range, so large,
 * volatile holdings are refined first and an asset whose price barely moved stops at its anchors.
 */
function bestRefinement(
  entry: BackfillAsset,
  range: BackfillRange,
  probes: readonly Probe[],
  heldShare: number,
): BackfillRequest | undefined {
  const minimumGap = 2 * sampleInterval(range);
  const length = Math.max(1, range.end - range.start);
  let best: BackfillRequest | undefined;
  for (let index = 1; index < probes.length; index++) {
    const left = probes[index - 1];
    const right = probes[index];
    const gap = right.time - left.time;
    if (gap < minimumGap)
      continue;
    const score = heldShare * move(left, right) * (gap / length);
    if (score < SCORE_FLOOR || (best && best.score >= score))
      continue;
    const half = Math.floor(gap / 2);
    best = {
      asset: entry.asset,
      excludeTimestamps: [left.time],
      fromTimestamp: left.time,
      interval: half,
      kind: 'refine',
      score,
      toTimestamp: left.time + half,
    };
  }
  return best;
}

/**
 * The next requests worth making, best first: missing anchors (largest holdings first), then the
 * highest-scoring gaps, at most one per asset so each request sees the previous one's prices.
 *
 * @param assets - what is cached and held per asset; the caller leaves spam out
 * @param range - the range the chart shows
 * @param limit - how many requests to return
 * @returns an empty list once every asset is refined to the chart's resolution
 */
export function planBackfill(assets: readonly BackfillAsset[], range: BackfillRange, limit: number): BackfillRequest[] {
  if (range.end < range.start)
    return [];
  const total = assets.reduce((sum, entry) => sum + Math.max(0, entry.heldValue.toNumber()), 0);
  if (total <= 0)
    return [];

  const anchors: [number, BackfillRequest][] = [];
  const refinements: BackfillRequest[] = [];
  for (const entry of assets) {
    const share = Math.max(0, entry.heldValue.toNumber()) / total;
    if (share < NEGLIGIBLE_SHARE)
      continue;
    const probes = probesOf(entry, range);
    const anchor = anchorRequest(entry, range, probes);
    if (anchor) {
      anchors.push([share, anchor]);
      continue;
    }
    const refinement = bestRefinement(entry, range, probes, share);
    if (refinement)
      refinements.push(refinement);
  }

  anchors.sort(([a], [b]) => b - a);
  refinements.sort((a, b) => b.score - a.score);
  return [...anchors.map(([, request]) => request), ...refinements].slice(0, limit);
}
