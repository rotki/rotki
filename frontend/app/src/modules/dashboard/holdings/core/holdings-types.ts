import type { BigNumber } from '@rotki/common';

/** A kind of place balances are held, in the order the dashboard lists them. */
export const SourceKind = {
  BLOCKCHAIN: 'blockchain',
  EXCHANGE: 'exchange',
  BANK: 'bank',
  MANUAL: 'manual',
} as const;

export type SourceKind = (typeof SourceKind)[keyof typeof SourceKind];

export const SOURCE_KIND_ORDER: readonly SourceKind[] = [
  SourceKind.BLOCKCHAIN,
  SourceKind.EXCHANGE,
  SourceKind.BANK,
  SourceKind.MANUAL,
];

interface ContributionValue {
  /** In the main currency, with ignored assets already left out. */
  readonly value: BigNumber;
  readonly loading: boolean;
}

/** One chain's or one location's share of a source, as the stores report it. */
export type SourceContribution =
  | ContributionValue & { readonly kind: typeof SourceKind.BLOCKCHAIN; readonly chain: string }
  | ContributionValue & {
    readonly kind: typeof SourceKind.EXCHANGE | typeof SourceKind.BANK | typeof SourceKind.MANUAL;
    readonly location: string;
  };

/** Value held outside the four sources that still counts toward net worth. */
export const ExtraKind = {
  NFT: 'nft',
} as const;

export type SummaryKind = SourceKind | (typeof ExtraKind)[keyof typeof ExtraKind];

export interface SourceTotal {
  readonly kind: SummaryKind;
  readonly value: BigNumber;
  /** Fraction of gross assets, between 0 and 1. */
  readonly share: BigNumber;
  /** Some of its value still waits on a price, so `value` and `share` are partial. */
  readonly loading: boolean;
}

export interface HoldingsSummary {
  /** Kinds holding value or still being priced, in {@link SOURCE_KIND_ORDER}, then NFTs when they count. */
  readonly sources: readonly SourceTotal[];
  /** Any source is still being priced, so no share is final yet. */
  readonly loading: boolean;
  /** Everything held, before liabilities. */
  readonly gross: BigNumber;
  readonly liabilities: BigNumber;
  /** Source kinds with nothing in them, offered as places to add balances. */
  readonly emptyKinds: readonly SourceKind[];
}

/** A table below the net worth card that a legend row scrolls to. */
export type LegendJump = 'nft' | 'liabilities';

/** Where a location tile leads. */
export type TileTarget =
  | { readonly type: 'chain'; readonly chain: string }
  | { readonly type: 'exchange'; readonly location: string }
  | { readonly type: 'bank' }
  | { readonly type: 'manual'; readonly location: string }
  | { readonly type: 'location'; readonly location: string };

/** What one source kind holds at a place. */
export interface HoldingPart {
  readonly kind: SourceKind;
  readonly value: BigNumber;
  readonly loading: boolean;
}

/**
 * A trade location, or a chain the backend has no location for.
 *
 * @remarks
 * `key` is the location identifier, or `chain:<id>` for a chain without one, so the two never collide.
 */
export type HoldingPlace =
  | { readonly key: string; readonly location: string; readonly chain: string | undefined }
  | { readonly key: string; readonly location: undefined; readonly chain: string };

/** Everything held at one place, whatever the sources it came from. */
export interface LocationHolding {
  readonly place: HoldingPlace;
  /** One per kind present, in {@link SOURCE_KIND_ORDER}. */
  readonly parts: readonly HoldingPart[];
  readonly value: BigNumber;
  readonly loading: boolean;
  readonly target: TileTarget;
}
