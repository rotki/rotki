import type { Exchange, QueryExchangeEventsPayload } from '@/modules/balances/types/exchanges';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

interface NonSyncingExchangesToggle {
  /** The list to persist as the `nonSyncingExchanges` setting. */
  readonly nonSyncingExchanges: QueryExchangeEventsPayload[];
  /** Whether the toggle turns syncing on for the exchange. */
  readonly enable: boolean;
}

interface UseNonSyncingExchangesReturn {
  isNonSyncExchange: (exchange: Exchange) => boolean;
  resetNonSyncingExchanges: () => void;
  toggleSync: (exchange: Exchange) => Promise<void>;
}

function isSameExchange(item: QueryExchangeEventsPayload, exchange: Exchange): boolean {
  return item.name === exchange.name && item.location === exchange.location;
}

/**
 * Flips syncing for one exchange: an exchange on the non-syncing list leaves it, any other joins it.
 * The given list is not modified.
 */
export function toggleNonSyncingExchange(
  current: readonly QueryExchangeEventsPayload[],
  exchange: Exchange,
): NonSyncingExchangesToggle {
  const index = current.findIndex(item => isSameExchange(item, exchange));

  if (index > -1)
    return { enable: true, nonSyncingExchanges: current.filter((_, i) => i !== index) };

  return {
    enable: false,
    nonSyncingExchanges: [...current, { location: exchange.location, name: exchange.name }],
  };
}

export function useNonSyncingExchanges(): UseNonSyncingExchangesReturn {
  const nonSyncingExchanges = ref<QueryExchangeEventsPayload[]>([]);

  const { t } = useI18n({ useScope: 'global' });
  const current = useSetting('nonSyncingExchanges');
  const { update } = useSettingsOperations();
  const { notify } = useNotificationDispatcher();

  function isNonSyncExchange(exchange: Exchange): boolean {
    return get(nonSyncingExchanges).some(item => isSameExchange(item, exchange));
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
      notify({
        display: true,
        message: t('exchange_settings.sync.messages.description', {
          action: enable ? t('exchange_settings.sync.messages.enable') : t('exchange_settings.sync.messages.disable'),
          location: exchange.location,
          message: status.message,
          name: exchange.name,
        }),
        title: t('exchange_settings.sync.messages.title'),
      });
    }

    resetNonSyncingExchanges();
  }

  return {
    isNonSyncExchange,
    resetNonSyncingExchanges,
    toggleSync,
  };
}
