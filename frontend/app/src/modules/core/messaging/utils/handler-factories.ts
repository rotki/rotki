import type { Notification } from '@rotki/common';
import type { MessageHandler, NotificationHandler, StateHandler } from '../interfaces';
import { logHandlerError } from './error-handling';

/**
 * Type aliases for factory function parameters
 */
type StateUpdateFn<T> = (data: T) => void | Promise<void>;

type NotificationFn<T> = (data: T) => Notification | Promise<Notification>;

type ConditionalHandlerFn<T> = (data: T) => Notification | null | void | Promise<Notification | null | void>;

type StateWithResultFn<T, R> = (data: T) => R | Promise<R>;

type ConditionalNotificationFn<T, R> = (data: T, result: R) => Notification | null | Promise<Notification | null>;

/**
 * Creates a simple state handler that only updates application state
 * @param updateFn - Function that performs the state update
 * @returns StateHandler that executes the update function
 */
export function createStateHandler<T>(
  updateFn: StateUpdateFn<T>,
): StateHandler<T> {
  return {
    handle: async (data: T): Promise<void> => {
      try {
        await updateFn(data);
      }
      catch (error: unknown) {
        logHandlerError(error, 'State handler execution failed');
      }
    },
  };
}

/**
 * Creates a notification handler that always produces a notification
 * @param notificationFn - Function that creates the notification
 * @returns NotificationHandler that creates and returns notifications
 */
export function createNotificationHandler<T>(
  notificationFn: NotificationFn<T>,
): NotificationHandler<T> {
  return {
    handle: async (data: T): Promise<Notification> => {
      try {
        return await notificationFn(data);
      }
      catch (error: unknown) {
        logHandlerError(error, 'Notification handler execution failed');
        throw error; // Re-throw to maintain NotificationHandler contract
      }
    },
  };
}

/**
 * Creates a conditional handler that may or may not produce notifications
 * @param handlerFn - Function that optionally creates notifications
 * @returns MessageHandler that handles conditional notification logic
 */
export function createConditionalHandler<T>(
  handlerFn: ConditionalHandlerFn<T>,
): MessageHandler<T> {
  return {
    handle: async (data: T): Promise<Notification | null | void> => {
      try {
        return await handlerFn(data);
      }
      catch (error: unknown) {
        logHandlerError(error, 'Conditional handler execution failed');
        return null; // Return null for failed conditional handlers to prevent crash
      }
    },
  };
}

/**
 * Creates a handler that updates state and conditionally shows notifications
 * @param updateFn - Function that performs state updates
 * @param notificationFn - Function that optionally creates notifications based on the result
 * @returns MessageHandler that combines state updates with conditional notifications
 */
export function createStateWithNotificationHandler<T, R = void>(
  updateFn: StateWithResultFn<T, R>,
  notificationFn: ConditionalNotificationFn<T, R>,
): MessageHandler<T> {
  return {
    handle: async (data: T): Promise<Notification | null | void> => {
      try {
        const result = await updateFn(data);
        return await notificationFn(data, result);
      }
      catch (error: unknown) {
        logHandlerError(error, 'State with notification handler execution failed');
        return null; // Return null to prevent notification on error
      }
    },
  };
}
