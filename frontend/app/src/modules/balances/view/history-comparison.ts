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
 * The rows of the view on show, plus a zero row for every asset of value only the other view holds.
 *
 * @remarks
 * Both views list the same assets this way, so switching between them changes amounts in place
 * instead of adding or removing rows; and an asset one side does not see at all, the largest
 * discrepancy there is, stays visible as a zero. The other side's price is kept so the row still
 * prices. Assets worth nothing on the other side, such as unpriced airdropped spam, are left out:
 * listed at zero they would bury the gaps that matter.
 */
export function withMissingAssets(
  shown: readonly AssetBalanceWithPriceAndChains[],
  other: readonly AssetBalanceWithPriceAndChains[],
): AssetBalanceWithPriceAndChains[] {
  const seen = new Set(shown.map(row => row.asset));
  const missing = other
    .filter(row => !seen.has(row.asset) && row.value.gt(0))
    .map((row): AssetBalanceWithPriceAndChains => ({ amount: Zero, asset: row.asset, price: row.price, value: Zero }));
  return [...shown, ...missing];
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
