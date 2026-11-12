import { type AssetBalanceWithPriceAndChains, type BigNumber, Zero } from '@rotki/common';

/** One asset's amount under both views, for the history view's "vs queried" readouts. */
export interface AssetComparison {
  readonly history: BigNumber;
  readonly queried: BigNumber;
  /** History minus queried; negative when history sees less. */
  readonly delta: BigNumber;
  /** The same difference in the main currency, for ranking gaps across assets. */
  readonly valueDelta: BigNumber;
  /**
   * The asset's amount in manual balances.
   *
   * @remarks
   * History has no events for manual balances, so this much of a negative `delta` is expected
   * rather than a derivation mismatch.
   */
  readonly manual: BigNumber;
}

function byAsset(rows: readonly AssetBalanceWithPriceAndChains[]): Map<string, AssetBalanceWithPriceAndChains> {
  return new Map(rows.map(row => [row.asset, row]));
}

/** A side that does not hold the asset holds zero of it. */
function amountOf(row: AssetBalanceWithPriceAndChains | undefined): BigNumber {
  return row?.amount ?? Zero;
}

function valueOf(row: AssetBalanceWithPriceAndChains | undefined): BigNumber {
  return row?.value ?? Zero;
}

/**
 * The history rows, plus a zero row for every asset of value only the queried side holds.
 *
 * @remarks
 * An asset that history does not see at all is the largest discrepancy there is, so the history view
 * lists it at zero instead of leaving it out. The queried price is kept so the row still prices.
 * Queried-only assets worth nothing, such as unpriced airdropped spam, are left out: listed at zero
 * they would bury the gaps that matter.
 */
export function withQueriedOnlyAssets(
  history: readonly AssetBalanceWithPriceAndChains[],
  queried: readonly AssetBalanceWithPriceAndChains[],
): AssetBalanceWithPriceAndChains[] {
  const seen = new Set(history.map(row => row.asset));
  const missing = queried
    .filter(row => !seen.has(row.asset) && row.value.gt(0))
    .map((row): AssetBalanceWithPriceAndChains => ({ amount: Zero, asset: row.asset, price: row.price, value: Zero }));
  return [...history, ...missing];
}

/** Per-asset amounts under both views, keyed by asset, for every asset either side holds. */
export function compareByAsset(
  history: readonly AssetBalanceWithPriceAndChains[],
  queried: readonly AssetBalanceWithPriceAndChains[],
  manual: readonly AssetBalanceWithPriceAndChains[],
): Map<string, AssetComparison> {
  const historyRows = byAsset(history);
  const queriedRows = byAsset(queried);
  const manualRows = byAsset(manual);
  const assets = new Set([...historyRows.keys(), ...queriedRows.keys()]);

  return new Map(Array.from(assets, (asset): [string, AssetComparison] => {
    const historyRow = historyRows.get(asset);
    const queriedRow = queriedRows.get(asset);
    return [asset, {
      delta: amountOf(historyRow).minus(amountOf(queriedRow)),
      history: amountOf(historyRow),
      manual: amountOf(manualRows.get(asset)),
      queried: amountOf(queriedRow),
      valueDelta: valueOf(historyRow).minus(valueOf(queriedRow)),
    }];
  }));
}
