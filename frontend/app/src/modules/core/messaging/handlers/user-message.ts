import type { MessageHandler } from '../interfaces';
import {
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
import { createConditionalHandler } from '../utils/handler-factories';
import { withRepeats } from '../utils/repeats';

/** The AuthFailure service the backend names for rotki's own premium credentials. */
const ROTKI_PREMIUM_SERVICE = 'rotki_premium';

/** Where a row keeps its latest sentence without the repeat count the message adds to it. */
const SENTENCE = 'sentence';

type AuthFields = Extract<UserMessageData, { key: typeof UserMessageKey.AUTH }>['fields'];

type ProblemMessage = Exclude<UserMessageData, { key: typeof UserMessageKey.AUTH }>;

/**
 * Renders a backend `add_error` / `add_warning` user message.
 *
 * @remarks
 * Rejected credentials create no notification: only the user can fix them, so they raise the
 * action center row that asks for the fix. Premium credentials raise the premium row, an exchange
 * account's the row for that account, and any other service's the missing key row, which stays
 * while the service has no key.
 *
 * Every other family folds into one row per family and identity (see `userMessageGroup`), which
 * keeps a count across repeats and across the ones the backend held while no client was connected.
 * The row shows the latest sentence and is `Priority.BULK`: recorded in the drawer, never popped.
 * The bulk of the corpus is self-describing as ignorable ("Ignoring it", "Skipping balance
 * result"), and a condition that warrants an interrupt earns it by getting a structured message
 * type, not by being a longer string.
 */
export function createUserMessageHandler(t: ReturnType<typeof useI18n>['t']): MessageHandler<UserMessageData> {
  const { data: notifications } = storeToRefs(useNotificationsStore());
  const { allExchanges } = storeToRefs(useLocationStore());
  const { getLocationData } = useLocations();
  const { raise } = useRaisedConditionsStore();

  function raiseRejectedCredentials({ account, service }: AuthFields): void {
    if (service === ROTKI_PREMIUM_SERVICE)
      raise({ cause: PremiumInactiveCause.EXPIRED, kind: RaisedConditionKind.PREMIUM_INACTIVE });
    else if (account && get(allExchanges).includes(service))
      raise({ kind: RaisedConditionKind.EXCHANGE_KEY_REJECTED, location: service, name: account });
    else
      raise({ kind: RaisedConditionKind.MISSING_API_KEY, service });
  }

  function nameOf(identifier: string): string {
    return getLocationData(identifier)?.name ?? toHumanReadable(identifier, 'capitalize');
  }

  function familyTitle(key: ProblemMessage['key']): string {
    switch (key) {
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

  function titleOf(data: ProblemMessage): string {
    const title = familyTitle(data.key);
    const subject = data.subject ? nameOf(data.subject) : undefined;
    return subject ? t('notification_messages.user_message.with_subject', { subject, title }) : title;
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

  return createConditionalHandler<UserMessageData>((data, { count, lastSent }) => {
    if (data.key === UserMessageKey.AUTH) {
      raiseRejectedCredentials(data.fields);
      return null;
    }

    const group = userMessageGroup(data);
    const row = get(notifications).find(notification => notification.group === group);
    const groupCount = (row?.groupCount ?? 0) + count;
    const sentence = latestSentence(data, row, lastSent);

    return {
      category: NotificationCategory.DEFAULT,
      extras: { [SENTENCE]: sentence },
      group,
      groupCount,
      message: withRepeats(t, sentence, groupCount),
      priority: Priority.BULK,
      severity: data.verbosity === MESSAGE_WARNING ? Severity.WARNING : Severity.ERROR,
      title: titleOf(data),
    };
  });
}
