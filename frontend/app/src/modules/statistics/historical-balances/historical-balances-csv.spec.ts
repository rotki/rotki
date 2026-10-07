import { bigNumberify } from '@rotki/common';
import dayjs from 'dayjs';
import { describe, expect, it } from 'vitest';
import { historicalBalancesCsv, type HistoricalBalancesCsvInput } from './historical-balances-csv';
import { type HistoricalBalanceRow, HistoricalBalancesMode, toViewRows } from './historical-balances-view';
import { PriceStatus } from './use-historical-balance-values';

const SYMBOLS: Record<string, string> = { DAI: 'DAI', ETH: 'ETH', RARE: 'RARE, the token', SCAM: 'SCAM' };

function rows(): HistoricalBalanceRow[] {
  const asset = (name: string, amount: string, price?: string, status: PriceStatus = PriceStatus.MISSING): Parameters<typeof toViewRows>[0][number] => ({
    amount: bigNumberify(amount),
    asset: name,
    buckets: [],
    price: price ? bigNumberify(price) : undefined,
    priceStatus: price ? PriceStatus.PRICED : status,
    value: price ? bigNumberify(amount).times(price) : undefined,
  });
  return toViewRows([
    asset('DAI', '10', '0.9'),
    asset('SCAM', '1000000', undefined, PriceStatus.SPAM),
    asset('ETH', '1.123456789012345678', '2000'),
    asset('RARE', '3'),
  ], HistoricalBalancesMode.FLAT, { collectionOf: () => undefined, mainAssetOf: () => undefined });
}

function input(overrides: Partial<HistoricalBalancesCsvInput> = {}): HistoricalBalancesCsvInput {
  return {
    currency: 'EUR',
    delimiter: ',',
    filter: '',
    rows: rows(),
    symbolOf: asset => SYMBOLS[asset] ?? asset,
    timestamp: dayjs('2024-12-31T23:59:59').unix(),
    timezone: 'Europe/Amsterdam',
    total: bigNumberify('2255.913578024691356'),
    ...overrides,
  };
}

function lines(csv: string): string[] {
  return csv.split('\n');
}

describe('historicalBalancesCsv', () => {
  it('should list each asset in table order under a header naming the currency, then the total', () => {
    const [header, ...body] = lines(historicalBalancesCsv(input()));

    expect(header).toBe('asset,symbol,amount,price_eur,value_eur,status');
    expect(body.slice(0, 5)).toEqual([
      'ETH,ETH,1.123456789012345678,2000,2246.913578024691356,priced',
      'DAI,DAI,10,0.9,9,priced',
      'RARE,"RARE, the token",3,,,no price',
      'SCAM,SCAM,1000000,,,spam',
      'total,,,,2255.913578024691356,',
    ]);
  });

  it('should close with the as-of time and timezone, the currency and what the balances leave out', () => {
    const tail = lines(historicalBalancesCsv(input())).slice(-4);

    expect(tail[0]).toBe('');
    expect(tail[1]).toMatch(/^as_of,2024-12-31 23:59:59 [+-]\d{2}:\d{2} \(Europe\/Amsterdam\)$/);
    expect(tail[2]).toBe('currency,EUR');
    expect(tail[3]).toMatch(/^note,"?Rebuilt from history events/);
  });

  it('should name the filter only when one narrowed the rows', () => {
    expect(historicalBalancesCsv(input())).not.toContain('\nfilter,');
    expect(historicalBalancesCsv(input({ filter: 'location: ethereum' }))).toContain('\nfilter,location: ethereum\n');
  });

  it('should quote a field holding the delimiter or a quote, doubling the quote', () => {
    const csv = historicalBalancesCsv(input({ delimiter: ';', symbolOf: asset => (asset === 'ETH' ? 'E;"TH"' : asset) }));

    expect(lines(csv)[1]).toBe('ETH;"E;""TH""";1.123456789012345678;2000;2246.913578024691356;priced');
  });

  it('should mark a partly priced collection as such', () => {
    const [partial] = rows();
    const csv = historicalBalancesCsv(input({ rows: [{ ...partial, partial: true }] }));

    expect(lines(csv)[1]).toMatch(/,partly priced$/);
  });
});
