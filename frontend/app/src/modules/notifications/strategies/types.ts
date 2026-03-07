import type { NotificationData, NotificationPayload, SemiPartial } from '@rotki/common';

export interface NotificationStrategyContext {
  readonly notifications: NotificationData[];
  readonly getNextId: () => number;
}

export interface NotificationStrategyResult {
  readonly notifications: NotificationData[];
}

export interface NotificationStrategy {
  /**
   * Attempt to handle the incoming notification.
   * Return a result to commit and stop the chain, or `undefined` to pass through.
   */
  process: (
    payload: SemiPartial<NotificationPayload, 'title' | 'message'>,
    context: NotificationStrategyContext,
  ) => NotificationStrategyResult | undefined;
}
