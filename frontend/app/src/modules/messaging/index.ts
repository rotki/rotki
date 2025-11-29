import { backoff } from '@shared/utils';
import { useSessionApi } from '@/composables/api/session';
import { camelCaseTransformer } from '@/modules/api/transformers';
import { useNotificationsStore } from '@/store/notifications';
import { uniqueStrings } from '@/utils/data';
import { logger } from '@/utils/logging';
import { createHandlerRegistry } from './handler-registry';
import { WebsocketMessage } from './messages';
import { MESSAGE_WARNING, SocketMessageType } from './types/base';
import { handleMessageError } from './utils/error-handling';

interface UseMessageHandling {
  handleMessage: (data: string) => Promise<void>;
  consume: () => Promise<void>;
}

export function useMessageHandling(): UseMessageHandling {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const { consumeMessages } = useSessionApi();
  const notificationsStore = useNotificationsStore();
  const { data: notifications } = storeToRefs(notificationsStore);
  const { notify } = notificationsStore;

  // Create registry with all handlers
  const registry = createHandlerRegistry(t, router);

  let isRunning = false;

  const handleMessage = async (data: string): Promise<void> => {
    const parseResult = WebsocketMessage.safeParse(camelCaseTransformer(JSON.parse(data)));

    if (!parseResult.success) {
      logger.warn(`Invalid websocket message format:`, parseResult.error, data);
      return;
    }

    const message = parseResult.data;
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

  const handlePollingMessage = async (message: string, isWarning: boolean): Promise<void> => {
    try {
      const object = JSON.parse(message);
      const parseResult = WebsocketMessage.safeParse(camelCaseTransformer(object));

      if (parseResult.success) {
        const handler = registry[parseResult.data.type];
        if (handler) {
          const result = await handler.handle(parseResult.data.data);
          if (result)
            notify(result);
        }
        else {
          logger.error('no handler for message type:', parseResult.data.type);
        }
      }
      else {
        // Fallback to legacy handler for invalid message format
        const handler = registry[SocketMessageType.LEGACY];
        const result = await handler.handle({ value: message, verbosity: isWarning ? MESSAGE_WARNING : '' });
        if (result)
          notify(result);
      }
    }
    catch {
      // JSON parse failed, use legacy handler
      const handler = registry[SocketMessageType.LEGACY];
      const result = await handler.handle({ value: message, verbosity: isWarning ? MESSAGE_WARNING : '' });
      if (result)
        notify(result);
    }
  };

  const consume = async (): Promise<void> => {
    if (isRunning)
      return;

    isRunning = true;
    const title = t('actions.notifications.consume.message_title');

    try {
      const messages = await backoff(3, async () => consumeMessages(), 10000);
      const existing = get(notifications).map(({ message }) => message);

      const errors = messages.errors
        .filter((error, ...args) => uniqueStrings(error, ...args) && !existing.includes(error));

      for (const message of errors) {
        await handlePollingMessage(message, false);
      }

      const warnings = messages.warnings
        .filter((warning, ...args) => uniqueStrings(warning, ...args) && !existing.includes(warning));

      for (const message of warnings) {
        await handlePollingMessage(message, true);
      }
    }
    catch (error: unknown) {
      const message = handleMessageError(error, 'Message consumption failed');
      notify({
        display: true,
        message,
        title,
      });
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
