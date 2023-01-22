import { type Ref } from 'vue';
import { api } from '@/services/rotkehlchen-api';
import { type Nullable } from '@/types';
import { startPromise } from '@/utils';
import { logger } from '@/utils/logging';

export const useWebsocketStore = defineStore('websocket', () => {
  const connection: Ref<Nullable<WebSocket>> = ref(null);
  const connected: Ref<boolean> = ref(false);

  const { handleMessage } = useMessageHandling();

  const reconnect = async (): Promise<void> => {
    logger.debug('Close was not clean attempting reconnect');
    try {
      await connect();
      logger.debug('websocket reconnection complete');
    } catch (e: any) {
      logger.debug(e, 'Reconnect failed');
    }
  };

  async function connect(): Promise<boolean> {
    return new Promise<boolean>(resolve => {
      if (get(connected)) {
        resolve(true);
        return;
      }
      const serverUrl = api.serverUrl;
      let protocol = 'ws';
      const location = window.location;
      if (
        serverUrl?.startsWith('https') ||
        location.protocol.startsWith('https')
      ) {
        protocol = 'wss';
      }
      const urlSegments = serverUrl.split('://');
      let baseUrl: string;
      if (urlSegments.length > 1) {
        baseUrl = urlSegments[1];
      } else {
        baseUrl = `${location.host}${location.pathname}`;
      }

      const url = `${protocol}://${baseUrl}/ws/`;
      logger.debug(`preparing to connect to ${url}`);
      const ws = new WebSocket(url);
      set(connection, ws);
      ws.onmessage = async (event): Promise<void> =>
        await handleMessage(event.data);
      ws.addEventListener('open', (): void => {
        logger.debug('websocket connected');
        set(connected, true);
        resolve(true);
      });
      ws.onerror = (): void => {
        logger.error('websocket connection failed');
        set(connected, false);
        resolve(false);
      };
      ws.addEventListener('close', (event): void => {
        logger.debug('websocket connection closed');
        set(connected, false);
        if (!event.wasClean) {
          startPromise(reconnect());
        }
      });
    });
  }

  const disconnect = (): void => {
    const ws = get(connection);
    if (!ws) {
      logger.debug('websocket was not connected');
      return;
    }
    ws.close();
    logger.debug('websocket was disconnected');
  };

  return {
    connected,
    connect,
    disconnect
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useWebsocketStore, import.meta.hot));
}
