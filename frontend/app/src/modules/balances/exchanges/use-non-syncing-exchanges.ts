import type { Exchange } from '@/modules/balances/types/exchanges';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

interface NonSyncingExchangesToggle {
  /** The connection identifiers to persist as the `nonSyncingExchanges` setting. */
  readonly nonSyncingExchanges: string[];
  /** Whether the toggle turns syncing on for the exchange. */
  readonly enable: boolean;
}

interface UseNonSyncingExchangesReturn {
  isNonSyncExchange: (exchange: Exchange) => boolean;
  resetNonSyncingExchanges: () => void;
  toggleSync: (exchange: Exchange) => Promise<void>;
}

/**
 * Flips syncing for one exchange: an exchange on the non-syncing list leaves it, any other joins it.
 * The given list is not modified.
 */
export function toggleNonSyncingExchange(
  current: readonly string[],
  exchange: Exchange,
): NonSyncingExchangesToggle {
  if (current.includes(exchange.identifier))
    return { enable: true, nonSyncingExchanges: current.filter(identifier => identifier !== exchange.identifier) };

  return { enable: false, nonSyncingExchanges: [...current, exchange.identifier] };
}

export function useNonSyncingExchanges(): UseNonSyncingExchangesReturn {
  const nonSyncingExchanges = ref<string[]>([]);

  const { t } = useI18n({ useScope: 'global' });
  const current = useSetting('nonSyncingExchanges');
  const { update } = useSettingsOperations();
  const { notifyInfo } = useNotifications();

  function isNonSyncExchange(exchange: Exchange): boolean {
    return get(nonSyncingExchanges).includes(exchange.identifier);
  }

  function resetNonSyncingExchanges(): void {
    set(nonSyncingExchanges, get(current));
  }

  async function toggleSync(exchange: Exchange): Promise<void> {
    const { enable, nonSyncingExchanges: data } = toggleNonSyncingExchange(get(nonSyncingExchanges), exchange);

    const status = await update({
      nonSyncingExchanges: data,
    });

    if (!status.success) {
      notifyInfo(
        t('exchange_settings.sync.messages.title'),
        t('exchange_settings.sync.messages.description', {
          action: enable ? t('exchange_settings.sync.messages.enable') : t('exchange_settings.sync.messages.disable'),
          location: exchange.location,
          message: status.message,
          name: exchange.name,
        }),
      );
    }

    resetNonSyncingExchanges();
  }

  return {
    isNonSyncExchange,
    resetNonSyncingExchanges,
    toggleSync,
  };
}
