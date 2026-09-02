/**
 * Shared types for amount display components.
 *
 * @packageDocumentation
 */

/**
 * A point in time, in whichever unit the caller holds.
 *
 * @remarks
 * A bare `number` is read as **seconds**; milliseconds must be wrapped as `\{ ms \}`. Passing
 * milliseconds bare floors to a near-zero key, so a historic price lookup silently finds nothing.
 */
export type Timestamp = number | { ms: number };

/**
 * Normalizes a Timestamp to seconds
 */
export function normalizeTimestamp(ts: Timestamp | undefined): number | undefined {
  if (ts === undefined) {
    return undefined;
  }
  if (typeof ts === 'number') {
    return ts;
  }
  return Math.floor(ts.ms / 1000);
}

/**
 * Rounding mode type for amount display.
 * - 'value': Use valueRoundingMode setting (default, typically ROUND_DOWN for fiat values)
 * - 'amount': Use amountRoundingMode setting (typically ROUND_UP for raw asset amounts)
 */
export type RoundingType = 'value' | 'amount';

/**
 * How to display currency symbol
 * - 'symbol': Use currency symbol (e.g., $, €)
 * - 'ticker': Use currency ticker (e.g., USD, EUR)
 * - 'none': No symbol displayed
 */
export type SymbolDisplay = 'symbol' | 'ticker' | 'none';

/**
 * Format options for display
 */
export interface FormatOptions {
  /** Display without decimals */
  integer?: boolean;
  /** Custom decimal places */
  decimals?: number;
  /**
   * Which rounding mode to use from frontend settings.
   * - 'value' (default): Uses valueRoundingMode setting (typically ROUND_DOWN)
   * - 'amount': Uses amountRoundingMode setting (typically ROUND_UP)
   */
  rounding?: RoundingType;
}
