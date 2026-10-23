import { describe, expect, it } from 'vitest';
import {
  allBalancesActivity,
  allBalancesLoginActivity,
  balancesRunActivity,
  chainBalancesActivity,
  exchangeBalancesActivity,
  exchangeSavingsActivity,
  manualBalanceAddActivity,
  manualBalanceEditActivity,
  manualBalancesFetchActivity,
  nftBalancesActivity,
  tokenDetectionActivity,
} from '@/modules/balances/balances.activity';
import { RefreshMode } from '@/modules/balances/types/refresh-mode';
import { setDigest } from '@/modules/core/common/data/digest';
import { BALANCES_LANE, EXCHANGE_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { activityIdHasPrefix } from '@/modules/task-center/core/types';

const address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

/** Literal ids on purpose, as in `decode.activity.spec.ts`. */
describe('chain balance activity ids', () => {
  it('should key a plain refresh by the chain alone', () => {
    expect(chainBalancesActivity.id({ chain: 'eth' })).toBe('blockchain-balances:eth');
  });

  it('should append detection after the chain, so detecting and plain refreshes never dedup', () => {
    expect(chainBalancesActivity.id({ chain: 'eth', detect: true })).toBe('blockchain-balances:eth:detect');
    expect(chainBalancesActivity.id({ chain: 'eth', detect: true, detectAddresses: [address] }))
      .toBe(`blockchain-balances:eth:detect:${setDigest([address])}`);
  });

  it('should ignore the address narrowing when the refresh does not detect', () => {
    expect(chainBalancesActivity.id({ chain: 'eth', detectAddresses: [address] })).toBe('blockchain-balances:eth');
  });

  it('should keep every variant under the chain prefix the readers ask by', () => {
    const within = chainBalancesActivity.partsWithin(['eth']);
    expect(within).toStrictEqual(['eth']);
    for (const subject of [{ chain: 'eth' }, { chain: 'eth', detect: true }, { chain: 'eth', detect: true, detectAddresses: [address] }])
      expect(activityIdHasPrefix(chainBalancesActivity.id(subject), chainBalancesActivity.kind, ...within)).toBe(true);
  });

  it('should keep the ledger parts of a plain refresh to the chain, which mark and invalidate write against', () => {
    expect(chainBalancesActivity.partsOf({ chain: 'eth' })).toStrictEqual(['eth']);
  });

  it('should run chain jobs on the balances lane', () => {
    expect(chainBalancesActivity.laneOf?.({ chain: 'eth' })).toBe(BALANCES_LANE);
  });

  it('should key a run by the chain set and mode, outside every chain prefix', () => {
    const id = balancesRunActivity.id({ chains: ['btc', 'eth'], mode: RefreshMode.USER });
    expect(id).toBe(`blockchain-balances:run:${setDigest(['btc', 'eth'])}:user`);
    expect(balancesRunActivity.id({ chains: ['eth', 'btc'], mode: RefreshMode.USER })).toBe(id);
    expect(balancesRunActivity.id({ chains: ['btc', 'eth'], mode: RefreshMode.BACKGROUND })).not.toBe(id);
    expect(activityIdHasPrefix(id, chainBalancesActivity.kind, 'eth')).toBe(false);
  });
});

describe('other balance activity ids', () => {
  it('should give the snapshot query the bare kind and the login one its own id', () => {
    expect(allBalancesActivity.id()).toBe('all-balances');
    expect(allBalancesLoginActivity.id()).toBe('all-balances:login');
  });

  it('should key manual balance saves by the balance', () => {
    expect(manualBalancesFetchActivity.id()).toBe('manual-balances:fetch');
    expect(manualBalanceAddActivity.id({ asset: 'ETH', label: 'Cold', location: 'external' })).toBe('manual-balances:add:external:ETH:Cold');
    expect(manualBalanceEditActivity.id({ identifier: 7 })).toBe('manual-balances:edit:7');
  });

  it('should give two concurrent additions with different labels distinct ids', () => {
    expect(manualBalanceAddActivity.id({ asset: 'ETH', label: 'Cold', location: 'external' }))
      .not
      .toBe(manualBalanceAddActivity.id({ asset: 'ETH', label: 'Hot', location: 'external' }));
  });

  it('should give the NFT balances the bare kind', () => {
    expect(nftBalancesActivity.id()).toBe('nft-balances');
  });

  it('should key exchange balances and savings by location, on the exchange lane', () => {
    expect(exchangeBalancesActivity.id({ location: 'kraken' })).toBe('exchange-balances:kraken');
    expect(exchangeSavingsActivity.id({ location: 'binance' })).toBe('exchange-savings:binance');
    expect(exchangeBalancesActivity.laneOf?.({ location: 'kraken' })).toBe(EXCHANGE_LANE);
    expect(exchangeSavingsActivity.laneOf?.({ location: 'binance' })).toBe(EXCHANGE_LANE);
  });

  it('should key token detection by chain and address, on the chain\'s own detect family', () => {
    expect(tokenDetectionActivity.id({ address, chain: 'eth' })).toBe(`token-detection:eth:${address}`);
    expect(tokenDetectionActivity.laneOf?.({ address, chain: 'eth' })).toBe('detect:eth');
  });
});
