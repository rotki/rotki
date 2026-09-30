import type { Notification } from '@rotki/common';
import type { SocketMessageType } from './types';

/**
 * How a message reached the frontend.
 *
 * @remarks
 * `count` is how many times the backend sent it: always 1 over the websocket, and more when the
 * backend held repeats of it while no client was connected and handed them over as one.
 * `lastSent` is set only for a held message, which can be read long after it was sent.
 */
export interface MessageDelivery {
  readonly count: number;
  readonly lastSent?: Date;
}

export const LIVE_DELIVERY: MessageDelivery = { count: 1 };

/**
 * Base message handler interface that can optionally create notifications.
 * - Return `Notification` to display a notification to the user
 * - Return `null` for state-only updates without notifications
 * - Return `void` for state-only updates (equivalent to null)
 */
export interface MessageHandler<T = any> {
  handle: (data: T, delivery?: MessageDelivery) => Promise<Notification | null | void>;
}

/**
 * Handler specifically for messages that only update application state
 * Use this for handlers that never create notifications
 */
export interface StateHandler<T = any> {
  handle: (data: T) => Promise<void>;
}

/**
 * Handler specifically for messages that always create notifications
 * Use this for handlers that always display something to the user
 */
export interface NotificationHandler<T = any> {
  handle: (data: T, delivery?: MessageDelivery) => Promise<Notification>;
}

/**
 * Registry mapping each socket message type to its corresponding handler
 */
export type MessageHandlerRegistry = Record<SocketMessageType, MessageHandler>;
