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
 *
 * @remarks
 * Penalties are grouped per oracle so a repeat replaces its earlier entry while failures of
 * different sources remain separate.
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
