import type { Router } from 'vue-router';
import type { NotificationHandler } from '../interfaces';
import type { OraclePenalizedData } from '@/modules/core/messaging/types';
import { NotificationCategory, NotificationGroup, Priority, Severity, toHumanReadable } from '@rotki/common';
import { createNotificationHandler } from '@/modules/core/messaging/utils';
import { SettingsCategoryIds } from '@/modules/settings/setting-highlight-ids';

const SECONDS_PER_MINUTE = 60;

/**
 * Explains a price load that suddenly leans on the other oracles: the backend set one aside
 * because it stopped answering (`timeout`) or kept failing (`errors`), for the penalty duration.
 */
export function createOraclePenalizedHandler(
  t: ReturnType<typeof useI18n>['t'],
  router: Pick<Router, 'push'>,
): NotificationHandler<OraclePenalizedData> {
  return createNotificationHandler<OraclePenalizedData>(({ oracle, penaltyDuration, reason }) => {
    const props = {
      minutes: Math.round(penaltyDuration / SECONDS_PER_MINUTE),
      oracle: toHumanReadable(oracle, 'capitalize'),
    };

    return {
      action: {
        action: async () => router.push({ name: '/settings/oracle/', hash: `#${SettingsCategoryIds.PRICE_ORACLE}` }),
        icon: 'lu-settings',
        label: t('notification_messages.oracle_penalized.action'),
        persist: true,
      },
      category: NotificationCategory.DEFAULT,
      display: true,
      // Per oracle: two sources set aside at the same time are two separate problems, while a
      // repeated penalty of the same source replaces its earlier entry.
      group: `${NotificationGroup.ORACLE_PENALIZED}:${oracle}`,
      message: reason === 'timeout'
        ? t('notification_messages.oracle_penalized.message_timeout', props)
        : t('notification_messages.oracle_penalized.message_errors', props),
      priority: Priority.ACTION,
      severity: Severity.WARNING,
      title: t('notification_messages.oracle_penalized.title', props),
    };
  });
}
