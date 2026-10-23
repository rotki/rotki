import { describe, expect, it } from 'vitest';
import {
  dailyPricesActivity,
  exchangeRatesActivity,
  historicPriceActivity,
  historicPriceBatchActivity,
  historicPriceWaveActivity,
  latestPricesActivity,
  latestPricesRefreshActivity,
  manualPriceAddActivity,
  manualPriceRemoveActivity,
  oracleCacheActivity,
} from '@/modules/assets/prices/prices.activity';
import { setDigest } from '@/modules/core/common/data/digest';
import { PRICE_REFRESH_LANE, UMBRELLA_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { type ActivityId, activityIdHasPrefix, ActivityKind } from '@/modules/task-center/core/types';

const assets = ['ETH', 'BTC'];

/** Whether `id` sits under `parts` of the PRICES kind, the question every prefix reader asks. */
function isUnder(id: ActivityId, parts: readonly (string | number)[]): boolean {
  return activityIdHasPrefix(id, ActivityKind.PRICES, ...parts);
}

/**
 * The ids are asserted as literals on purpose, as in `decode.activity.spec.ts`: comparing a
 * descriptor against itself holds whatever it produces, so a changed id shape would pass while the
 * readers that ask by prefix silently stopped matching.
 */
describe('price activity ids', () => {
  it('should give the oracle cache its fixed id', () => {
    expect(oracleCacheActivity.id()).toBe('prices:oracle-cache');
  });

  it('should key exchange rates by currency, so a switch mid-fetch is a second fetch rather than a join', () => {
    expect(exchangeRatesActivity.id({ currency: 'EUR' })).toBe('prices:exchange-rates:EUR');
    expect(exchangeRatesActivity.id({ currency: 'GBP' })).not.toBe(exchangeRatesActivity.id({ currency: 'EUR' }));
  });

  it('should keep every currency under the exchange-rates prefix the refresh button reads', () => {
    const within = exchangeRatesActivity.partsWithin([]);
    expect(within).toStrictEqual(['exchange-rates']);
    expect(isUnder(exchangeRatesActivity.id({ currency: 'GBP' }), within)).toBe(true);
  });

  it('should key a manual price save by its pair and a delete by its asset', () => {
    expect(manualPriceAddActivity.id({ fromAsset: 'ETH', toAsset: 'EUR' })).toBe('prices:manual:add:ETH:EUR');
    expect(manualPriceRemoveActivity.id({ fromAsset: 'ETH' })).toBe('prices:manual:remove:ETH');
  });

  it('should give saves for two assets distinct ids, so one never joins the other', () => {
    expect(manualPriceAddActivity.id({ fromAsset: 'ETH', toAsset: 'EUR' }))
      .not
      .toBe(manualPriceAddActivity.id({ fromAsset: 'BTC', toAsset: 'EUR' }));
    expect(manualPriceRemoveActivity.id({ fromAsset: 'ETH' })).not.toBe(manualPriceRemoveActivity.id({ fromAsset: 'BTC' }));
  });

  it('should key a latest-price query by the asset set digest and the cache flag', () => {
    const digest = setDigest(assets);
    expect(latestPricesActivity.id({ ignoreCache: false, selectedAssets: assets })).toBe(`prices:latest:${digest}:cached`);
    expect(latestPricesActivity.id({ ignoreCache: true, selectedAssets: assets })).toBe(`prices:latest:${digest}:pull`);
  });

  it('should give the same asset set in another order the same id, so one query joins the other', () => {
    expect(latestPricesActivity.id({ ignoreCache: false, selectedAssets: ['BTC', 'ETH'] }))
      .toBe(latestPricesActivity.id({ ignoreCache: false, selectedAssets: ['ETH', 'BTC'] }));
  });

  it('should give different asset sets distinct ids, so a form query never joins the background sweep', () => {
    expect(latestPricesActivity.id({ ignoreCache: false, selectedAssets: ['ETH'] }))
      .not
      .toBe(latestPricesActivity.id({ ignoreCache: false, selectedAssets: assets }));
  });

  it('should end a balance refresh id in balances, so it never joins a plain query of the same set', () => {
    const subject = { ignoreCache: true, selectedAssets: assets };
    expect(latestPricesRefreshActivity.id(subject)).toBe(`prices:latest:${setDigest(assets)}:pull:balances`);
    expect(latestPricesRefreshActivity.id(subject)).not.toBe(latestPricesActivity.id(subject));
  });

  it('should keep both latest-price shapes under the latest prefix the refresh button reads', () => {
    const within = latestPricesActivity.partsWithin([]);
    expect(within).toStrictEqual(['latest']);
    expect(isUnder(latestPricesActivity.id({ ignoreCache: false, selectedAssets: assets }), within)).toBe(true);
    expect(isUnder(latestPricesRefreshActivity.id({ ignoreCache: false, selectedAssets: assets }), within)).toBe(true);
  });

  it('should key a historic price by pair and timestamp', () => {
    expect(historicPriceActivity.id({ fromAsset: 'ETH', timestamp: 1700000000, toAsset: 'USD' })).toBe('prices:historic:ETH:USD:1700000000');
  });

  it('should give two moments of one pair distinct ids', () => {
    expect(historicPriceActivity.id({ fromAsset: 'ETH', timestamp: 1, toAsset: 'USD' }))
      .not
      .toBe(historicPriceActivity.id({ fromAsset: 'ETH', timestamp: 2, toAsset: 'USD' }));
  });

  it('should key batches and waves by sequence under the batch prefix', () => {
    expect(historicPriceBatchActivity.id({ sequence: 3 })).toBe('prices:historic:batch:3');
    expect(historicPriceWaveActivity.id({ sequence: 3 })).toBe('prices:historic:batch:all:3');
  });

  it('should let a batch-progress frame reach batches and waves without driving a single-pair query', () => {
    const batchPrefix = historicPriceBatchActivity.partsWithin(['batch']);
    expect(batchPrefix).toStrictEqual(['historic', 'batch']);
    expect(isUnder(historicPriceBatchActivity.id({ sequence: 1 }), batchPrefix)).toBe(true);
    expect(isUnder(historicPriceWaveActivity.id({ sequence: 1 }), batchPrefix)).toBe(true);
    expect(isUnder(historicPriceActivity.id({ fromAsset: 'ETH', timestamp: 1, toAsset: 'USD' }), batchPrefix)).toBe(false);
  });

  it('should keep single pairs, batches and waves under the historic prefix a currency change cancels', () => {
    const within = historicPriceActivity.partsWithin([]);
    expect(within).toStrictEqual(['historic']);
    for (const id of [
      historicPriceActivity.id({ fromAsset: 'ETH', timestamp: 1, toAsset: 'USD' }),
      historicPriceBatchActivity.id({ sequence: 1 }),
      historicPriceWaveActivity.id({ sequence: 1 }),
    ]) {
      expect(isUnder(id, within)).toBe(true);
    }
  });

  it('should key daily prices by asset, interval and range', () => {
    expect(dailyPricesActivity.id({ asset: 'ETH', fromTimestamp: 10, interval: 86400, toTimestamp: 20 })).toBe('prices:daily:ETH:86400:10:20');
    expect(dailyPricesActivity.partsWithin([])).toStrictEqual(['daily']);
  });

  it('should keep manual add and remove under the manual prefix the NFT balances go stale on', () => {
    const within = manualPriceAddActivity.partsWithin([]);
    expect(within).toStrictEqual(['manual']);
    expect(isUnder(manualPriceAddActivity.id({ fromAsset: 'ETH', toAsset: 'EUR' }), within)).toBe(true);
    expect(isUnder(manualPriceRemoveActivity.id({ fromAsset: 'ETH' }), within)).toBe(true);
  });
});

describe('price activity lanes', () => {
  it('should run a balance refresh on the price refresh lane, one at a time', () => {
    expect(latestPricesRefreshActivity.laneOf?.({ ignoreCache: false, selectedAssets: assets })).toBe(PRICE_REFRESH_LANE);
  });

  it('should run a wave on the umbrella lane, so waiting for its batches never holds one of their slots', () => {
    expect(historicPriceWaveActivity.laneOf?.({ sequence: 1 })).toBe(UMBRELLA_LANE);
  });

  it('should leave a plain latest-price query and a batch on no declared lane', () => {
    expect(latestPricesActivity.laneOf).toBeUndefined();
    expect(historicPriceBatchActivity.laneOf).toBeUndefined();
  });
});
