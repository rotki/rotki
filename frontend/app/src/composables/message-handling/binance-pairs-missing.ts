import type { BinancePairsMissingData, CommonMessageHandler } from '@/types/websocket-messages';
import { type Notification, Priority, Severity } from '@rotki/common';
import { Routes } from '@/router/routes';

export function useBinancePairsMissingHandler(t: ReturnType<typeof useI18n>['t']): CommonMessageHandler<BinancePairsMissingData> {
  const router = useRouter();

  const handle = (data: BinancePairsMissingData): Notification => {
    const { location, name } = data;

    return {
      action: {
        action: async () => router.push({
          path: Routes.API_KEYS_EXCHANGES.toString(),
          query: { location, name },
        }),
        label: t('notification_messages.binance_pairs_missing.action'),
        persist: true,
      },
      display: true,
      message: t('notification_messages.binance_pairs_missing.message', { name }),
      priority: Priority.ACTION,
      severity: Severity.WARNING,
      title: t('notification_messages.binance_pairs_missing.title'),
    };
  };

  return { handle };
}
