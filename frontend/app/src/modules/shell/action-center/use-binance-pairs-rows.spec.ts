import type { EffectScope } from 'vue';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useBinancePairsRows } from '@/modules/shell/action-center/use-binance-pairs-rows';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

const { queryBinanceUserMarkets, show, suppressed, updateFrontendSetting } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    queryBinanceUserMarkets: vi.fn<(name: string, location: string) => Promise<string[]>>(),
    show: vi.fn<(message: { title: string; message: string }, onConfirm: () => Promise<void>) => void>(),
    suppressed: ref<string[]>([]),
    updateFrontendSetting: vi.fn<(payload: object) => Promise<{ success: boolean }>>(),
  };
});

vi.mock('@/modules/balances/api/use-exchange-api', () => ({
  useExchangeApi: (): object => ({ queryBinanceUserMarkets }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): object => suppressed,
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): object => ({ updateFrontendSetting }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): object => ({ show }),
}));

let scope: EffectScope | undefined;

function binanceRows(): ReturnType<typeof useBinancePairsRows> {
  scope = effectScope();
  const result = scope.run(() => useBinancePairsRows());
  assert(result);
  return result;
}

describe('modules/shell/action-center/use-binance-pairs-rows', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(suppressed, []);
    updateFrontendSetting.mockResolvedValue({ success: true });
    useConnectedExchangesStore().setConnectedExchanges([{ location: 'binance', name: 'main' }]);
    useRaisedConditionsStore().raise({ kind: RaisedConditionKind.BINANCE_PAIRS_MISSING, location: 'binance', name: 'main' });
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should raise a row per reported account, leading to its pair selection', () => {
    const [row] = get(binanceRows().rows);

    expect(row.id).toBe('binance-pairs-missing-binance-main');
    expect(row.title).toBe('action_center.rows.integrations.binance_pairs_missing.title::Binance, main');
    expect(row.target).toEqual({ kind: 'route', to: { name: '/api-keys/exchanges/', query: { location: 'binance', name: 'main' } } });
  });

  it('should take the row down once the account is removed or renamed', async () => {
    const { rows } = binanceRows();

    useConnectedExchangesStore().setConnectedExchanges([{ location: 'binance', name: 'renamed' }]);
    await nextTick();

    expect(get(rows)).toEqual([]);
  });

  it('should take the row down on a re-check that finds pairs', async () => {
    queryBinanceUserMarkets.mockResolvedValue(['ETHBTC']);
    const { refresh, rows } = binanceRows();

    await refresh();

    expect(get(rows)).toEqual([]);
  });

  it('should hide an account the user asked not to be told about again', () => {
    set(suppressed, ['binance:main']);

    expect(get(binanceRows().rows)).toEqual([]);
  });

  it('should ask before suppressing an account, then add it to the suppressed accounts', async () => {
    set(suppressed, ['binanceus:other']);
    const option = get(binanceRows().rows)[0].options.find(({ id }) => id === 'do-not-show-again');
    assert(option?.target.kind === 'run');
    option.target.run();

    expect(updateFrontendSetting).not.toHaveBeenCalled();
    const [message, onConfirm] = show.mock.calls[0];
    expect(message.title).toBe('action_center.rows.integrations.binance_pairs_missing.suppress_confirm.title::Binance, main');
    await onConfirm();

    expect(updateFrontendSetting).toHaveBeenCalledWith({ suppressBinancePairsMissing: ['binanceus:other', 'binance:main'] });
  });
});
