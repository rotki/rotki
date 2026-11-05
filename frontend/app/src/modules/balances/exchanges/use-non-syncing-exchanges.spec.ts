import type { Exchange } from '@/modules/balances/types/exchanges';
import type { ActionStatus } from '@/modules/core/common/action';
import { createTestExchange } from '@test/utils/create-data';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { toggleNonSyncingExchange, useNonSyncingExchanges } from '@/modules/balances/exchanges/use-non-syncing-exchanges';

const stored = ref<string[]>([]);

const { spies } = vi.hoisted(() => ({
  spies: {
    notifyInfo: vi.fn<(title: string, message: string) => void>(),
    update: vi.fn(),
  },
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<string[]> => stored,
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): object => ({ update: spies.update }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): object => ({ notifyInfo: spies.notifyInfo }),
}));

const kraken: Exchange = createTestExchange('kraken', 'main');
const binance: Exchange = createTestExchange('binance', 'main');
const coinbase: Exchange = createTestExchange('coinbase', 'savings');

function ids(...exchanges: Exchange[]): string[] {
  return exchanges.map(exchange => exchange.identifier);
}

describe('toggleNonSyncingExchange', () => {
  it('should resume syncing only the toggled exchange and keep the others paused', () => {
    const result = toggleNonSyncingExchange(ids(kraken, binance, coinbase), kraken);

    expect(result.nonSyncingExchanges).toEqual(ids(binance, coinbase));
    expect(result.enable).toBe(true);
  });

  it('should keep the exchanges on both sides of the toggled one paused', () => {
    const result = toggleNonSyncingExchange(ids(kraken, binance, coinbase), binance);

    expect(result.nonSyncingExchanges).toEqual(ids(kraken, coinbase));
  });

  it('should pause an exchange that is syncing', () => {
    const result = toggleNonSyncingExchange(ids(kraken), binance);

    expect(result.nonSyncingExchanges).toEqual(ids(kraken, binance));
    expect(result.enable).toBe(false);
  });

  it('should match on the connection identifier, not the location or name', () => {
    const krakenSecond: Exchange = createTestExchange('kraken', 'second');
    const renamedKraken: Exchange = { ...kraken, name: 'renamed' };

    expect(toggleNonSyncingExchange(ids(kraken), krakenSecond).nonSyncingExchanges).toEqual(ids(kraken, krakenSecond));
    expect(toggleNonSyncingExchange(ids(kraken), renamedKraken).nonSyncingExchanges).toEqual([]);
  });

  it('should store only the identifier of a paused exchange', () => {
    const result = toggleNonSyncingExchange([], { ...kraken, krakenAccountType: 'pro' });

    expect(result.nonSyncingExchanges).toEqual([kraken.identifier]);
  });

  it('should leave the given list unchanged', () => {
    const current = ids(kraken, binance);

    toggleNonSyncingExchange(current, kraken);
    toggleNonSyncingExchange(current, coinbase);

    expect(current).toEqual(ids(kraken, binance));
  });
});

describe('useNonSyncingExchanges', () => {
  function succeed(): ActionStatus {
    return { success: true };
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(stored, ids(kraken, binance, coinbase));
    spies.update.mockResolvedValue(succeed());
  });

  it('should report the exchanges the stored setting pauses once reset', () => {
    const { isNonSyncExchange, resetNonSyncingExchanges } = useNonSyncingExchanges();

    expect(isNonSyncExchange(kraken)).toBe(false);

    resetNonSyncingExchanges();

    expect(isNonSyncExchange(kraken)).toBe(true);
    expect(isNonSyncExchange(createTestExchange('kraken', 'second'))).toBe(false);
  });

  it('should save the list minus only the exchange being resumed', async () => {
    const { resetNonSyncingExchanges, toggleSync } = useNonSyncingExchanges();
    resetNonSyncingExchanges();

    await toggleSync(kraken);

    expect(spies.update).toHaveBeenCalledExactlyOnceWith({ nonSyncingExchanges: ids(binance, coinbase) });
    expect(spies.notifyInfo).not.toHaveBeenCalled();
  });

  it('should show the saved setting after the toggle', async () => {
    const { isNonSyncExchange, resetNonSyncingExchanges, toggleSync } = useNonSyncingExchanges();
    resetNonSyncingExchanges();
    spies.update.mockImplementation(async ({ nonSyncingExchanges }: { nonSyncingExchanges: string[] }) => {
      set(stored, nonSyncingExchanges);
      return succeed();
    });

    await toggleSync(kraken);

    expect(isNonSyncExchange(kraken)).toBe(false);
    expect(isNonSyncExchange(binance)).toBe(true);
    expect(isNonSyncExchange(coinbase)).toBe(true);
  });

  it('should say enabling failed when resuming an exchange cannot be saved', async () => {
    const { resetNonSyncingExchanges, toggleSync } = useNonSyncingExchanges();
    resetNonSyncingExchanges();
    spies.update.mockResolvedValue({ message: 'backend down', success: false });

    await toggleSync(kraken);

    expect(spies.notifyInfo).toHaveBeenCalledOnce();
    const [, message] = spies.notifyInfo.mock.calls[0];
    expect(message).toContain('exchange_settings.sync.messages.enable');
    expect(message).not.toContain('exchange_settings.sync.messages.disable');
  });

  it('should say disabling failed when pausing an exchange cannot be saved', async () => {
    set(stored, []);
    const { resetNonSyncingExchanges, toggleSync } = useNonSyncingExchanges();
    resetNonSyncingExchanges();
    spies.update.mockResolvedValue({ message: 'backend down', success: false });

    await toggleSync(kraken);

    const [, message] = spies.notifyInfo.mock.calls[0];
    expect(message).toContain('exchange_settings.sync.messages.disable');
  });
});
