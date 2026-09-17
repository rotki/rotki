import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { LocationHolding, SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { bigNumberSum } from '@/modules/core/common/data/calculation';
import { narrowToKind } from '@/modules/dashboard/holdings/core/location-holdings';
import { splitVisible, visibleTileCount } from '@/modules/dashboard/holdings/core/tile-cap';

/**
 * Matches the `minmax(210px, 1fr)` columns and `gap-2` of the tile grid.
 *
 * @remarks
 * 210px is what a large holding needs to keep its value and share on one line; narrower columns
 * wrap the share onto a second line and leave the row ragged.
 */
const TILE_GRID = { gap: 8, minWidth: 210, rows: 2 } as const;

interface LocationsStripInput {
  readonly holdings: MaybeRefOrGetter<readonly LocationHolding[]>;
  /** A kind picked in the legend, or `undefined` for every kind. */
  readonly kind: MaybeRefOrGetter<SourceKind | undefined>;
  /** The grid's content width in pixels. */
  readonly width: MaybeRefOrGetter<number>;
  readonly modelExpanded: Ref<boolean>;
}

interface UseLocationsStripReturn {
  readonly visible: ComputedRef<readonly LocationHolding[]>;
  readonly hiddenCount: ComputedRef<number>;
  readonly hiddenValue: ComputedRef<BigNumber>;
  /** What each tile's share is measured against: every tile shown, before the cap. */
  readonly base: ComputedRef<BigNumber>;
  /** Whether the grid overflows two rows, so the toggle has something to do. */
  readonly canExpand: ComputedRef<boolean>;
}

/** The tiles the dashboard shows, narrowed to a kind and capped at two rows unless expanded. */
export function useLocationsStrip({ holdings, kind, modelExpanded, width }: LocationsStripInput): UseLocationsStripReturn {
  const narrowed = computed<readonly LocationHolding[]>(() => {
    const selected = toValue(kind);
    const all = toValue(holdings);
    return selected ? narrowToKind(all, selected) : all;
  });

  const split = computed(() => splitVisible(get(narrowed), visibleTileCount(toValue(width), TILE_GRID)));

  return {
    base: computed<BigNumber>(() => bigNumberSum(get(narrowed).map(holding => holding.value))),
    canExpand: computed<boolean>(() => get(split).hidden.length > 0),
    hiddenCount: computed<number>(() => (get(modelExpanded) ? 0 : get(split).hidden.length)),
    hiddenValue: computed<BigNumber>(() => get(split).hiddenValue),
    visible: computed<readonly LocationHolding[]>(() => (get(modelExpanded) ? get(narrowed) : get(split).visible)),
  };
}
