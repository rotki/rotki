import { NotificationGroup, type NotificationGroupKey } from '@rotki/common';
import { type UserMessageData, UserMessageKey } from './types/base';

/**
 * The values that decide which row a user message folds into, besides its family and verbosity.
 *
 * @remarks
 * The grain differs per family. Unreadable data and an unreachable remote fold per location and
 * record, because forty kucoin balances that failed to parse are one problem. Rejected credentials
 * stay per account and unknown assets per asset, since folding them would hide which key needs
 * replacing or which asset needs adding. The
 * free-text `error` never takes part: it varies between repeats of the same failure.
 */
function identityOf(data: UserMessageData): (string | null)[] {
  switch (data.key) {
    case UserMessageKey.AUTH:
      return [data.fields.service, data.fields.account];
    case UserMessageKey.BAD_DATA:
    case UserMessageKey.NETWORK:
      return [data.subject, data.fields.record];
    case UserMessageKey.INTERNAL:
      return [data.fields.operation];
    case UserMessageKey.LOCAL_DB:
      return [data.fields.entry];
    case UserMessageKey.PRICE:
      return [data.subject];
    case UserMessageKey.UNKNOWN_ASSET:
      return [data.subject, data.fields.identifier];
    case UserMessageKey.UNSUPPORTED:
      return [data.subject, data.fields.feature];
  }
}

/** The notification group a backend user message collapses into. */
export function userMessageGroup(data: UserMessageData): NotificationGroupKey {
  return `${NotificationGroup.USER_MESSAGE}:${JSON.stringify([data.verbosity, data.key, ...identityOf(data)])}`;
}
