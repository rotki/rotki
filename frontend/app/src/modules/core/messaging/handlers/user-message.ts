import type { RouteLocationRaw, Router } from 'vue-router';
import type { NotificationHandler } from '../interfaces';
import {
  type NotificationAction,
  NotificationCategory,
  type NotificationData,
  Priority,
  Severity,
  toHumanReadable,
} from '@rotki/common';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useLocations } from '@/modules/core/common/use-locations';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import {
  PremiumInactiveCause,
  RaisedConditionKind,
  useRaisedConditionsStore,
} from '@/modules/shell/action-center/use-raised-conditions-store';
import { MESSAGE_WARNING, type UserMessageData, UserMessageKey } from '../types/base';
import { userMessageGroup } from '../user-message-group';
import { createNotificationHandler } from '../utils/handler-factories';
import { withRepeats } from '../utils/repeats';

/** The AuthFailure service the backend names for rotki's own premium credentials. */
const ROTKI_PREMIUM_SERVICE = 'rotki_premium';

/** Where a row keeps its latest sentence without the repeat count the message adds to it. */
const SENTENCE = 'sentence';

type AuthFields = Extract<UserMessageData, { key: typeof UserMessageKey.AUTH }>['fields'];

/**
 * Renders a backend `add_error` / `add_warning` user message.
 *
 * @remarks
 * Messages fold into one row per family and identity (see `userMessageGroup`), which keeps a
 * count across repeats and across the ones the backend held while no client was connected. The
 * row shows the latest sentence.
 *
 * Only rejected credentials interrupt, because only the user can fix them, and they come with a
 * route to the keys. Rejected premium credentials instead raise the action center's premium row,
 * which already asks for a working key, so they are recorded without popping. Every other family
 * is `Priority.BULK`: recorded in the drawer, never popped.
 * The bulk of the corpus is self-describing as ignorable ("Ignoring it", "Skipping balance
 * result"), and a condition that warrants an interrupt earns it by getting a structured message
 * type, not by being a longer string.
 */
export function createUserMessageHandler(
  t: ReturnType<typeof useI18n>['t'],
  router: Pick<Router, 'push'>,
): NotificationHandler<UserMessageData> {
  const { data: notifications } = storeToRefs(useNotificationsStore());
  const { allExchanges } = storeToRefs(useLocationStore());
  const { getLocationData } = useLocations();
  const { raise } = useRaisedConditionsStore();

  function isRejectedPremiumKey(data: UserMessageData): boolean {
    return data.key === UserMessageKey.AUTH && data.fields.service === ROTKI_PREMIUM_SERVICE;
  }

  function nameOf(identifier: string): string {
    return getLocationData(identifier)?.name ?? toHumanReadable(identifier, 'capitalize');
  }

  function familyTitle(key: UserMessageKey): string {
    switch (key) {
      case UserMessageKey.AUTH:
        return t('notification_messages.user_message.title.auth');
      case UserMessageKey.BAD_DATA:
        return t('notification_messages.user_message.title.bad_data');
      case UserMessageKey.INTERNAL:
        return t('notification_messages.user_message.title.internal');
      case UserMessageKey.LOCAL_DB:
        return t('notification_messages.user_message.title.local_db');
      case UserMessageKey.NETWORK:
        return t('notification_messages.user_message.title.network');
      case UserMessageKey.PRICE:
        return t('notification_messages.user_message.title.price');
      case UserMessageKey.UNKNOWN_ASSET:
        return t('notification_messages.user_message.title.unknown_asset');
      case UserMessageKey.UNSUPPORTED:
        return t('notification_messages.user_message.title.unsupported');
    }
  }

  /** Who the message is about: the account whose credentials failed, or the location. */
  function subjectOf(data: UserMessageData): string | undefined {
    if (data.key === UserMessageKey.AUTH) {
      const { account, service } = data.fields;
      return account ? `${nameOf(service)} (${account})` : nameOf(service);
    }
    return data.subject ? nameOf(data.subject) : undefined;
  }

  function titleOf(data: UserMessageData): string {
    const title = familyTitle(data.key);
    const subject = subjectOf(data);
    return subject ? t('notification_messages.user_message.with_subject', { subject, title }) : title;
  }

  function credentialsRoute({ account, service }: AuthFields): RouteLocationRaw {
    if (service === ROTKI_PREMIUM_SERVICE)
      return { name: '/api-keys/premium/' };
    if (get(allExchanges).includes(service))
      return { name: '/api-keys/exchanges/', query: { location: service, ...(account && { name: account }) } };
    return { name: '/api-keys/external/', query: { service } };
  }

  function credentialsAction(data: UserMessageData): NotificationAction | undefined {
    if (data.key !== UserMessageKey.AUTH)
      return undefined;

    const route = credentialsRoute(data.fields);
    return {
      action: async () => router.push(route),
      label: t('notification_messages.user_message.auth_action'),
      persist: true,
    };
  }

  /**
   * The sentence the row shows: the newest one sent.
   *
   * @remarks
   * A repeat the backend held can be older than what the row already shows, such as one a dying
   * connection never delivered, handed back after a newer one arrived live. The row keeps its own.
   */
  function latestSentence(data: UserMessageData, row: NotificationData | undefined, lastSent: Date | undefined): string {
    const rowSentence = row?.extras?.[SENTENCE];
    if (row && lastSent && lastSent < row.date && typeof rowSentence === 'string')
      return rowSentence;
    return data.value;
  }

  return createNotificationHandler<UserMessageData>((data, { count, lastSent }) => {
    const group = userMessageGroup(data);
    const row = get(notifications).find(notification => notification.group === group);
    const groupCount = (row?.groupCount ?? 0) + count;
    const sentence = latestSentence(data, row, lastSent);
    const action = credentialsAction(data);
    const hasPremiumRow = isRejectedPremiumKey(data);
    if (hasPremiumRow)
      raise({ cause: PremiumInactiveCause.EXPIRED, kind: RaisedConditionKind.PREMIUM_INACTIVE });

    return {
      ...(action && { action }),
      ...(hasPremiumRow && { display: false }),
      category: NotificationCategory.DEFAULT,
      extras: { [SENTENCE]: sentence },
      group,
      groupCount,
      message: withRepeats(t, sentence, groupCount),
      priority: action ? Priority.ACTION : Priority.BULK,
      severity: data.verbosity === MESSAGE_WARNING ? Severity.WARNING : Severity.ERROR,
      title: titleOf(data),
    };
  });
}
