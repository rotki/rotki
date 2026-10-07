import type { UserMessageData } from './types/base';
import { NotificationGroup, type NotificationGroupKey } from '@rotki/common';

/**
 * The notification group a backend user message collapses into.
 *
 * @remarks
 * The identity is the backend's `group`, which each message family declares once and the backend
 * also holds undelivered repeats by, so the row a message folds into and the count the backend
 * reports for it agree.
 */
export function userMessageGroup(data: UserMessageData): NotificationGroupKey {
  return `${NotificationGroup.USER_MESSAGE}:${JSON.stringify(data.group)}`;
}
