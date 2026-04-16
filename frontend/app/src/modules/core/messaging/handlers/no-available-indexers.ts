import type { NotificationHandler } from '../interfaces';
import type { NoAvailableIndexersData } from '@/modules/core/messaging/types';
import { NotificationCategory, NotificationGroup, Priority, Severity, toHumanReadable } from '@rotki/common';
import { createNotificationHandler } from '@/modules/core/messaging/utils';
import { Routes } from '@/router/routes';

export function createNoAvailableIndexersHandler(t: ReturnType<typeof useI18n>['t'], router: ReturnType<typeof useRouter>): NotificationHandler<NoAvailableIndexersData> {
  return createNotificationHandler<NoAvailableIndexersData>(({ chain }) => ({
    action: {
      action: async () => router.push({ path: Routes.SETTINGS_EVM.toString(), hash: '#indexer' }),
      label: t('notification_messages.no_available_indexers.action'),
      persist: true,
    },
    category: NotificationCategory.DEFAULT,
    display: true,
    group: NotificationGroup.NO_AVAILABLE_INDEXERS,
    message: t('notification_messages.no_available_indexers.message', { chain: toHumanReadable(chain, 'capitalize') }),
    priority: Priority.ACTION,
    severity: Severity.WARNING,
    title: t('notification_messages.no_available_indexers.title'),
  }));
}
