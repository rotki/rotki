import { pipe } from 'plainfp';
import { filter, flatMap, groupBy, map } from 'plainfp/arrays';
import { values } from 'plainfp/records';
import { bigNumberSum } from '@/modules/core/common/data/calculation';
import {
  type HoldingPart,
  type HoldingPlace,
  type LocationHolding,
  SOURCE_KIND_ORDER,
  type SourceContribution,
  SourceKind,
  type TileTarget,
} from './holdings-types';

interface MergeOptions {
  /** The trade location a chain's balances show under, when the backend has one. */
  readonly locationOfChain: (chain: string) => string | undefined;
}

interface Placed {
  readonly place: HoldingPlace;
  readonly contribution: SourceContribution;
}

function placeOf(contribution: SourceContribution, { locationOfChain }: MergeOptions): HoldingPlace {
  if (contribution.kind !== SourceKind.BLOCKCHAIN)
    return { chain: undefined, key: contribution.location, location: contribution.location };

  const location = locationOfChain(contribution.chain);
  return location
    ? { chain: contribution.chain, key: location, location }
    : { chain: contribution.chain, key: `chain:${contribution.chain}`, location: undefined };
}

/**
 * Where a tile leads.
 *
 * @remarks
 * A place held through one kind keeps the page that kind always opened. A place held through several
 * opens the location page, which lists all of them. A chain without a location can only be held on
 * chain, so it always opens its chain page.
 */
export function tileTarget(place: HoldingPlace, kinds: readonly SourceKind[]): TileTarget {
  if (place.location === undefined)
    return { chain: place.chain, type: 'chain' };

  const { location } = place;
  if (kinds.length !== 1)
    return { location, type: 'location' };

  switch (kinds[0]) {
    case SourceKind.BLOCKCHAIN:
      return place.chain ? { chain: place.chain, type: 'chain' } : { location, type: 'location' };
    case SourceKind.EXCHANGE:
      return { location, type: 'exchange' };
    case SourceKind.BANK:
      return { type: 'bank' };
    case SourceKind.MANUAL:
      return { location, type: 'manual' };
  }
}

function partsOf(contributions: readonly SourceContribution[]): HoldingPart[] {
  return pipe(
    SOURCE_KIND_ORDER,
    map(kind => ({ kind, ofKind: contributions.filter(contribution => contribution.kind === kind) })),
    filter(({ ofKind }) => ofKind.length > 0),
    map(({ kind, ofKind }) => ({
      kind,
      loading: ofKind.some(contribution => contribution.loading),
      value: bigNumberSum(ofKind.map(contribution => contribution.value)),
    })),
  );
}

function holdingOf(place: HoldingPlace, parts: readonly HoldingPart[]): LocationHolding {
  return {
    loading: parts.some(part => part.loading),
    parts,
    place,
    target: tileTarget(place, parts.map(part => part.kind)),
    value: bigNumberSum(parts.map(part => part.value)),
  };
}

function byValue(holdings: LocationHolding[]): LocationHolding[] {
  return [...holdings].sort((a, b) => b.value.comparedTo(a.value) ?? 0);
}

/**
 * Folds every source's contributions into one holding per place.
 *
 * @remarks
 * Places are trade locations, so an exchange and a manual balance at Kraken share a tile, and a
 * manual balance recorded at `ethereum` joins the Ethereum chain. A chain the backend has no
 * location for, such as ETH2, keeps a tile of its own. Places with nothing in them are dropped
 * unless they are still loading.
 */
export function mergeLocations(contributions: readonly SourceContribution[], options: MergeOptions): LocationHolding[] {
  return pipe(
    contributions,
    map((contribution): Placed => ({ contribution, place: placeOf(contribution, options) })),
    groupBy(({ place }) => place.key),
    values,
    map(atPlace => holdingOf(atPlace[0].place, partsOf(atPlace.map(({ contribution }) => contribution)))),
    filter(holding => holding.loading || !holding.value.isZero()),
    byValue,
  );
}

/** The holdings a kind contributes to, each showing only that kind's part. */
export function narrowToKind(holdings: readonly LocationHolding[], kind: SourceKind): LocationHolding[] {
  return pipe(
    holdings,
    flatMap(holding => holding.parts
      .filter(part => part.kind === kind)
      .map(part => holdingOf(holding.place, [part]))),
    byValue,
  );
}
