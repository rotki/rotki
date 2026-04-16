import type { NotificationStrategy } from './types';
import { assert, NotificationGroup } from '@rotki/common';
import { createNotification } from '@/modules/notifications/notification-utils';

const BEACONCHAIN_RATE_LIMITED_PREFIX = 'Beaconcha.in is rate limited';

interface BeaconchainRateLimitedExtras extends Record<string, unknown> {
  endpoints: string[];
  until?: string;
}

function extractUntil(message: string): string {
  const match = message.match(/Beaconcha\.in is rate limited until ([^.]+)\./);
  return match?.[1] ?? '';
}

function formatUntil(until: string | undefined): string {
  return until ? ` until ${until}` : '';
}

function isBeaconchainExtras(extras: Record<string, unknown>): extras is BeaconchainRateLimitedExtras {
  return Array.isArray(extras.endpoints) && extras.endpoints.every(item => typeof item === 'string');
}

export function createBeaconchainRateLimitStrategy(
  t: ReturnType<typeof useI18n>['t'],
): NotificationStrategy {
  return {
    process(payload, context): ReturnType<NotificationStrategy['process']> {
      if (!payload.message.includes(BEACONCHAIN_RATE_LIMITED_PREFIX))
        return undefined;

      const notifications = [...context.notifications];
      const index = notifications.findIndex(
        notification => notification.group === NotificationGroup.BEACONCHAIN_RATE_LIMITED,
      );

      const newUntil = extractUntil(payload.message);
      const endpoint = payload.title;

      if (index >= 0) {
        const existing = notifications[index];
        assert(existing.groupCount !== undefined, 'groupCount should be defined when group is set');
        assert(
          existing.extras !== undefined && isBeaconchainExtras(existing.extras),
          'extras should be defined for beaconchain rate limit group',
        );

        const { endpoints: existingEndpoints, until: existingUntil } = existing.extras;

        if (existingEndpoints.includes(endpoint))
          return { notifications };

        const endpoints = [...existingEndpoints, endpoint];
        const groupCount = endpoints.length;
        const until = newUntil || existingUntil;

        notifications[index] = {
          ...existing,
          date: new Date(),
          display: true,
          extras: { endpoints, until },
          groupCount,
          message: t('notification_messages.beaconchain_rate_limited.message', {
            count: groupCount,
            endpoints: endpoints.map(item => `- ${item}`).join('\n'),
            until: formatUntil(until),
          }),
        };
      }
      else {
        const endpoints = [endpoint];
        const extras: BeaconchainRateLimitedExtras = { endpoints, until: newUntil || undefined };

        notifications.push(createNotification(context.getNextId(), {
          ...payload,
          display: true,
          extras,
          group: NotificationGroup.BEACONCHAIN_RATE_LIMITED,
          groupCount: 1,
          message: t('notification_messages.beaconchain_rate_limited.message', {
            count: 1,
            endpoints: `- ${endpoint}`,
            until: formatUntil(newUntil),
          }),
          title: t('notification_messages.beaconchain_rate_limited.title'),
        }));
      }

      return { notifications };
    },
  };
}
