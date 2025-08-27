import type { NotificationHandler } from '../interfaces';
import type { BinancePairsMissingData } from '@/modules/messaging/types';
import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { createNotificationHandler } from '@/modules/messaging/utils';
import { Routes } from '@/router/routes';

export function createBinancePairsMissingHandler(t: ReturnType<typeof useI18n>['t'], router: ReturnType<typeof useRouter>): NotificationHandler<BinancePairsMissingData> {
  return createNotificationHandler<BinancePairsMissingData>(({ location, name }) => ({
    action: {
      action: async () => router.push({
        path: Routes.API_KEYS_EXCHANGES.toString(),
        query: { location, name },
      }),
      label: t('notification_messages.binance_pairs_missing.action'),
      persist: true,
    },
    category: NotificationCategory.DEFAULT,
    display: true,
    message: t('notification_messages.binance_pairs_missing.message', { name }),
    priority: Priority.ACTION,
    severity: Severity.WARNING,
    title: t('notification_messages.binance_pairs_missing.title'),
  }));
}
