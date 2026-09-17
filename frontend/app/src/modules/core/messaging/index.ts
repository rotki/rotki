import { Priority } from '@rotki/common';
import { backoff } from '@shared/utils';
import { camelCaseTransformer } from '@/modules/core/api/transformers';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { useSessionApi } from '@/modules/session/api/use-session-api';
import { createHandlerRegistry } from './handler-registry';
import { WebsocketMessage } from './messages';
import { SocketMessageType } from './types/base';
import { handleMessageError } from './utils/error-handling';

/**
 * Validate one `{ type, data }` message, from the websocket or from the polling fallback.
 *
 * @returns The message, or undefined after logging it when it fails the schema.
 */
function parseMessage(raw: unknown): WebsocketMessage | undefined {
  const parseResult = WebsocketMessage.safeParse(camelCaseTransformer(raw));
  if (!parseResult.success) {
    logger.warn('Invalid message format:', parseResult.error, raw);
    return undefined;
  }
  return parseResult.data;
}

/**
 * What makes two polled messages the same notification.
 *
 * @remarks
 * A user message is identified by the text it renders, so it also matches a notification the
 * websocket already delivered. Any other message is identified by its whole content.
 */
function pollingKey(message: WebsocketMessage): string {
  return message.type === SocketMessageType.USER_MESSAGE ? message.data.value : JSON.stringify(message);
}

interface UseMessageHandling {
  handleMessage: (data: string) => Promise<void>;
  consume: () => Promise<void>;
}

export function useMessageHandling(): UseMessageHandling {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const { consumeMessages } = useSessionApi();
  const { data: notifications } = storeToRefs(useNotificationsStore());
  const { notify } = useNotificationDispatcher();

  const registry = createHandlerRegistry(t, router);

  let isRunning = false;

  const route = async (message: WebsocketMessage): Promise<void> => {
    const handler = registry[message.type];

    if (!handler) {
      logger.warn(`No handler found for socket message type: '${message.type}'`);
      return;
    }

    const result = await handler.handle(message.data);
    // Handler can return Notification, null, or void - only notify if we get a Notification
    if (result) {
      notify(result);
    }
  };

  const handleMessage = async (data: string): Promise<void> => {
    const message = parseMessage(JSON.parse(data));
    if (message)
      await route(message);
  };

  const consume = async (): Promise<void> => {
    if (isRunning)
      return;

    isRunning = true;
    const title = t('actions.notifications.consume.message_title');

    try {
      const { errors, warnings } = await backoff(3, async () => consumeMessages(), 10000);
      const shown = new Set<string>(get(notifications).map(({ message }) => message));

      for (const raw of [...errors, ...warnings]) {
        const message = parseMessage(raw);
        if (!message || shown.has(pollingKey(message)))
          continue;

        shown.add(pollingKey(message));
        await route(message);
      }
    }
    catch (error: unknown) {
      const message = handleMessageError(error, 'Message consumption failed');
      notify({ message, priority: Priority.NORMAL, title });
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
