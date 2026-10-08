import type { BigNumber } from '@rotki/common';
import dayjs from 'dayjs';
import { type HistoricalBalanceRow, sortRows } from '@/modules/statistics/historical-balances/historical-balances-view';
import { PriceStatus } from '@/modules/statistics/historical-balances/use-historical-balance-values';

export interface HistoricalBalancesCsvInput {
  rows: readonly HistoricalBalanceRow[];
  total: BigNumber;
  /** The as-of time, in unix seconds. */
  timestamp: number;
  /** The user's main currency, which every price and value is in. */
  currency: string;
  delimiter: string;
  /** The IANA timezone the as-of time is shown in. */
  timezone: string;
  /** What the rows were narrowed to, already described; empty when nothing was filtered. */
  filter: string;
  symbolOf: (asset: string) => string;
}

/** Read under every export, because history events are the only thing these balances come from. */
const COVERAGE_NOTE = 'Rebuilt from history events. Holdings without history events, such as manual balances, liabilities and ETH staking validators, are not included.';

const STATUS_LABEL: Readonly<Record<PriceStatus, string>> = {
  [PriceStatus.PRICED]: 'priced',
  [PriceStatus.PENDING]: 'pending',
  [PriceStatus.MISSING]: 'no price',
  [PriceStatus.SPAM]: 'spam',
};

function statusOf(row: HistoricalBalanceRow): string {
  return row.partial ? 'partly priced' : STATUS_LABEL[row.priceStatus];
}

/** Quotes a field holding the delimiter, a quote, a line break or surrounding spaces. */
function escapeField(value: string, delimiter: string): string {
  const needsQuotes = value.includes(delimiter) || /["\n\r]/.test(value) || value.trim() !== value;
  return needsQuotes ? `"${value.replaceAll('"', '""')}"` : value;
}

/**
 * The balances of one day as CSV: one line per row in table order, a total, then what the file
 * stands for.
 *
 * @remarks
 * Made for a wealth tax return, such as the Dutch Box 3, which asks what everything was worth at a
 * moment. The trailing lines name that moment with its offset and timezone, the currency, any filter,
 * and what the balances leave out, so the file still says what it is once it is passed on. Numbers
 * keep their full precision and are never scrambled. A row without a price keeps its amount, with no
 * value and a status saying why.
 */
export function historicalBalancesCsv(input: HistoricalBalancesCsvInput): string {
  const { currency, delimiter, filter, rows, symbolOf, timestamp, timezone, total } = input;
  const line = (fields: string[]): string => fields.map(field => escapeField(field, delimiter)).join(delimiter);
  const unit = currency.toLowerCase();

  return [
    line(['asset', 'symbol', 'amount', `price_${unit}`, `value_${unit}`, 'status']),
    ...sortRows(rows).map(row => line([
      row.asset,
      symbolOf(row.asset),
      row.amount.toFixed(),
      row.price?.toFixed() ?? '',
      row.value?.toFixed() ?? '',
      statusOf(row),
    ])),
    line(['total', '', '', '', total.toFixed(), '']),
    '',
    line(['as_of', `${dayjs.unix(timestamp).format('YYYY-MM-DD HH:mm:ss Z')} (${timezone})`]),
    line(['currency', currency]),
    ...(filter ? [line(['filter', filter])] : []),
    line(['note', COVERAGE_NOTE]),
  ].join('\n');
}
