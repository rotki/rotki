import type { Exchange, QueryExchangeEventsPayload } from '@/modules/balances/types/exchanges';
import type { ActionStatus } from '@/modules/core/common/action';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { toggleNonSyncingExchange, useNonSyncingExchanges } from '@/modules/balances/exchanges/use-non-syncing-exchanges';

const stored = ref<QueryExchangeEventsPayload[]>([]);

const { spies } = vi.hoisted(() => ({
  spies: {
    notify: vi.fn(),
    update: vi.fn(),
  },
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<QueryExchangeEventsPayload[]> => stored,
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): object => ({ update: spies.update }),
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: (): object => ({ notify: spies.notify }),
}));

const kraken: Exchange = { location: 'kraken', name: 'main' };
const binance: Exchange = { location: 'binance', name: 'main' };
const coinbase: Exchange = { location: 'coinbase', name: 'savings' };

describe('toggleNonSyncingExchange', () => {
  it('should resume syncing only the toggled exchange and keep the others paused', () => {
    const result = toggleNonSyncingExchange([kraken, binance, coinbase], kraken);

    expect(result.nonSyncingExchanges).toEqual([binance, coinbase]);
    expect(result.enable).toBe(true);
  });

  it('should keep the exchanges on both sides of the toggled one paused', () => {
    const result = toggleNonSyncingExchange([kraken, binance, coinbase], binance);

    expect(result.nonSyncingExchanges).toEqual([kraken, coinbase]);
  });

  it('should pause an exchange that is syncing', () => {
    const result = toggleNonSyncingExchange([kraken], binance);

    expect(result.nonSyncingExchanges).toEqual([kraken, binance]);
    expect(result.enable).toBe(false);
  });

  it('should match on location and name together', () => {
    const krakenSecond: Exchange = { location: 'kraken', name: 'second' };

    expect(toggleNonSyncingExchange([kraken], krakenSecond).nonSyncingExchanges).toEqual([kraken, krakenSecond]);
    expect(toggleNonSyncingExchange([kraken], binance).nonSyncingExchanges).toEqual([kraken, binance]);
  });

  it('should store only the location and name of a paused exchange', () => {
    const result = toggleNonSyncingExchange([], { krakenAccountType: 'pro', location: 'kraken', name: 'main' });

    expect(result.nonSyncingExchanges).toEqual([{ location: 'kraken', name: 'main' }]);
  });

  it('should leave the given list unchanged', () => {
    const current = [kraken, binance];

    toggleNonSyncingExchange(current, kraken);
    toggleNonSyncingExchange(current, coinbase);

    expect(current).toEqual([kraken, binance]);
  });
});

describe('useNonSyncingExchanges', () => {
  function succeed(): ActionStatus {
    return { success: true };
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(stored, [kraken, binance, coinbase]);
    spies.update.mockResolvedValue(succeed());
  });

  it('should report the exchanges the stored setting pauses once reset', () => {
    const { isNonSyncExchange, resetNonSyncingExchanges } = useNonSyncingExchanges();

    expect(isNonSyncExchange(kraken)).toBe(false);

    resetNonSyncingExchanges();

    expect(isNonSyncExchange(kraken)).toBe(true);
    expect(isNonSyncExchange({ location: 'kraken', name: 'second' })).toBe(false);
  });

  it('should save the list minus only the exchange being resumed', async () => {
    const { resetNonSyncingExchanges, toggleSync } = useNonSyncingExchanges();
    resetNonSyncingExchanges();

    await toggleSync(kraken);

    expect(spies.update).toHaveBeenCalledExactlyOnceWith({ nonSyncingExchanges: [binance, coinbase] });
    expect(spies.notify).not.toHaveBeenCalled();
  });

  it('should show the saved setting after the toggle', async () => {
    const { isNonSyncExchange, resetNonSyncingExchanges, toggleSync } = useNonSyncingExchanges();
    resetNonSyncingExchanges();
    spies.update.mockImplementation(async ({ nonSyncingExchanges }: { nonSyncingExchanges: QueryExchangeEventsPayload[] }) => {
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

    expect(spies.notify).toHaveBeenCalledOnce();
    const [{ message }] = spies.notify.mock.calls[0];
    expect(message).toContain('exchange_settings.sync.messages.enable');
    expect(message).not.toContain('exchange_settings.sync.messages.disable');
  });

  it('should say disabling failed when pausing an exchange cannot be saved', async () => {
    set(stored, []);
    const { resetNonSyncingExchanges, toggleSync } = useNonSyncingExchanges();
    resetNonSyncingExchanges();
    spies.update.mockResolvedValue({ message: 'backend down', success: false });

    await toggleSync(kraken);

    const [{ message }] = spies.notify.mock.calls[0];
    expect(message).toContain('exchange_settings.sync.messages.disable');
  });
});
