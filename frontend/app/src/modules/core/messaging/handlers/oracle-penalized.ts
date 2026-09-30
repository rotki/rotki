import type { Router } from 'vue-router';
import type { MessageHandler } from '../interfaces';
import type { OraclePenalizedData } from '@/modules/core/messaging/types';
import { NotificationCategory, NotificationGroup, Priority, Severity, toHumanReadable } from '@rotki/common';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { withRepeats } from '@/modules/core/messaging/utils/repeats';
import { SettingsCategoryIds } from '@/modules/settings/setting-highlight-ids';

const SECONDS_PER_MINUTE = 60;
const MS_PER_SECOND = 1000;

/**
 * Explains a price load that suddenly leans on the other oracles: the backend set one aside
 * because it stopped answering (`timeout`) or kept failing (`errors`), for the penalty duration.
 *
 * @remarks
 * Penalties are grouped per oracle so a repeat replaces its earlier entry while failures of
 * different sources remain separate. A penalty the backend held while no client was connected
 * is shown only if it is still running: once it has run out, the oracle is back in use and the
 * notification would describe a state that no longer exists.
 */
export function createOraclePenalizedHandler(
  t: ReturnType<typeof useI18n>['t'],
  router: Pick<Router, 'push'>,
): MessageHandler<OraclePenalizedData> {
  return createConditionalHandler<OraclePenalizedData>(({ oracle, penaltyDuration, reason }, { count, lastSent }) => {
    if (lastSent && lastSent.getTime() + penaltyDuration * MS_PER_SECOND < Date.now())
      return null;

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
      message: withRepeats(t, reason === 'timeout'
        ? t('notification_messages.oracle_penalized.message_timeout', props)
        : t('notification_messages.oracle_penalized.message_errors', props), count),
      priority: Priority.HIGH,
      severity: Severity.WARNING,
      title: t('notification_messages.oracle_penalized.title', props),
    };
  });
}
