import { Priority, Severity } from '@rotki/common';
import { backoff } from '@shared/utils';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { camelCaseTransformer } from '@/modules/core/api/transformers';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { sessionWorkSignal } from '@/modules/core/session/session-lifecycle';
import { useSessionApi } from '@/modules/session/api/use-session-api';
import { createHandlerRegistry } from './handler-registry';
import { LIVE_DELIVERY, type MessageDelivery } from './interfaces';
import { WebsocketMessage } from './messages';
import { handleMessageError } from './utils/error-handling';

/**
 * Validate one camelCased `{ type, data }` message, from the websocket or from the polling fallback.
 *
 * @remarks
 * The api client already camelCases a polled response, so only the websocket path transforms.
 *
 * @returns The message, or undefined after logging it when it fails the schema.
 */
function parseMessage(raw: unknown): WebsocketMessage | undefined {
  const parseResult = WebsocketMessage.safeParse(raw);
  if (!parseResult.success) {
    logger.warn('Invalid message format:', parseResult.error, raw);
    return undefined;
  }
  return parseResult.data;
}

interface UseMessageHandling {
  handleMessage: (data: string) => Promise<void>;
  consume: () => Promise<void>;
}

export function useMessageHandling(): UseMessageHandling {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const { consumeMessages } = useSessionApi();
  const { notify } = useNotificationDispatcher();

  const registry = createHandlerRegistry(t, router);

  let isRunning = false;

  const route = async (message: WebsocketMessage, delivery: MessageDelivery = LIVE_DELIVERY): Promise<void> => {
    const handler = registry[message.type];

    if (!handler) {
      logger.warn(`No handler found for socket message type: '${message.type}'`);
      return;
    }

    const result = await handler.handle(message.data, delivery);
    // Handler can return Notification, null, or void - only notify if we get a Notification
    if (result) {
      notify(delivery.lastSent ? { ...result, date: delivery.lastSent } : result);
    }
  };

  const handleMessage = async (data: string): Promise<void> => {
    const message = parseMessage(camelCaseTransformer(JSON.parse(data)));
    if (message)
      await route(message);
  };

  const consume = async (): Promise<void> => {
    if (isRunning)
      return;

    isRunning = true;
    const title = t('actions.notifications.consume.message_title');

    try {
      const { dropped, messages } = await backoff(3, async () => consumeMessages(), 10000, sessionWorkSignal());

      for (const { count, lastSent, ...raw } of messages) {
        const message = parseMessage(raw);
        if (message)
          await route(message, { count, lastSent: new Date(lastSent * 1000) });
      }

      if (dropped > 0) {
        notify({
          message: t('actions.notifications.consume.dropped', { count: dropped }),
          priority: Priority.NORMAL,
          severity: Severity.WARNING,
          title,
        });
      }
    }
    catch (error: unknown) {
      if (isRequestCancellation(error))
        return;
      const message = handleMessageError(error, 'Message consumption failed');
      notify({ message, priority: Priority.NORMAL, severity: Severity.ERROR, title });
    }
    finally {
      isRunning = false;
    }
  };

  return {
    consume,
    handleMessage,
  };
}
