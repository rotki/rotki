import type { ExchangeFormData } from '@/modules/balances/types/exchanges';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';
import { useBinancePairsConditions } from './use-binance-pairs-conditions';

const { queryBinanceUserMarkets } = vi.hoisted(() => ({
  queryBinanceUserMarkets: vi.fn<(name: string, location: string) => Promise<string[]>>(),
}));

vi.mock('@/modules/balances/api/use-exchange-api', () => ({
  useExchangeApi: (): object => ({ queryBinanceUserMarkets }),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { error: vi.fn() },
}));

function raise(location: string, name: string): void {
  useRaisedConditionsStore().raise({ kind: RaisedConditionKind.BINANCE_PAIRS_MISSING, location, name });
}

function form(overrides: Partial<ExchangeFormData>): ExchangeFormData {
  return { apiKey: '', apiSecret: '', location: 'binance', mode: 'edit', name: 'main', passphrase: '', ...overrides };
}

describe('modules/balances/exchanges/use-binance-pairs-conditions', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    raise('binance', 'main');
    raise('binance', 'second');
  });

  it('should list the reported accounts', () => {
    expect(get(useBinancePairsConditions().accounts)).toEqual([
      { location: 'binance', name: 'main' },
      { location: 'binance', name: 'second' },
    ]);
  });

  it('should settle only the account just saved with pairs', () => {
    const { accounts, settleSaved } = useBinancePairsConditions();

    settleSaved(form({ binanceMarkets: ['ETHBTC'] }));

    expect(get(accounts)).toEqual([{ location: 'binance', name: 'second' }]);
  });

  it('should settle the accounts that are no longer connected', () => {
    const { accounts, settleDisconnected } = useBinancePairsConditions();

    settleDisconnected([{ location: 'binance', name: 'second' }, { location: 'kraken', name: 'main' }]);

    expect(get(accounts)).toEqual([{ location: 'binance', name: 'second' }]);
  });

  it('should leave other kinds of conditions alone', () => {
    useRaisedConditionsStore().raise({ kind: RaisedConditionKind.MISSING_API_KEY, service: 'etherscan' });

    useBinancePairsConditions().settleDisconnected([]);

    expect(useRaisedConditionsStore().conditions).toEqual([{ kind: RaisedConditionKind.MISSING_API_KEY, service: 'etherscan' }]);
  });

  it('should settle on a re-check the accounts that have pairs now, reading each one', async () => {
    queryBinanceUserMarkets.mockImplementation(async name => (name === 'main' ? ['ETHBTC'] : []));
    const { accounts, recheck } = useBinancePairsConditions();

    await recheck();

    expect(queryBinanceUserMarkets).toHaveBeenCalledWith('main', 'binance');
    expect(queryBinanceUserMarkets).toHaveBeenCalledWith('second', 'binance');
    expect(get(accounts)).toEqual([{ location: 'binance', name: 'second' }]);
  });

  it('should keep an account listed when its pairs cannot be read', async () => {
    queryBinanceUserMarkets.mockRejectedValue(new Error('offline'));
    const { accounts, recheck } = useBinancePairsConditions();

    await recheck();

    expect(get(accounts)).toHaveLength(2);
  });
});
