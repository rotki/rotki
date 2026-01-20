import type { Nullable } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { api } from '@/modules/api/rotki-api';
import { useMessageHandling } from '@/modules/messaging';
import { delay } from '@/utils/async-utilities';
import { logger } from '@/utils/logging';

/** Delay in milliseconds before attempting to reconnect to websocket */
const RECONNECT_DELAY_MS = 2000;

export const useWebsocketStore = defineStore('websocket', () => {
  const connection = ref<Nullable<WebSocket>>(null);
  const connected = ref<boolean>(false);
  /** When false, connection attempts are blocked (e.g., backend failed to start) */
  const connectionEnabled = ref<boolean>(true);

  const { handleMessage } = useMessageHandling();

  const reconnect = async (): Promise<void> => {
    if (!get(connectionEnabled)) {
      logger.debug('Websocket reconnection skipped - connection disabled');
      return;
    }
    logger.debug(`Close was not clean, waiting ${RECONNECT_DELAY_MS}ms before reconnect`);
    await delay(RECONNECT_DELAY_MS);
    try {
      await connect();
      logger.debug('websocket reconnection complete');
    }
    catch (error: any) {
      logger.debug(error, 'Reconnect failed');
    }
  };

  async function connect(): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      if (!get(connectionEnabled)) {
        logger.debug('Websocket connection skipped - connection disabled');
        resolve(false);
        return;
      }
      if (get(connected)) {
        resolve(true);
        return;
      }
      const serverUrl = api.serverUrl;
      let protocol = 'ws';
      const location = window.location;
      if (serverUrl?.startsWith('https') || location.protocol.startsWith('https'))
        protocol = 'wss';

      const urlSegments = serverUrl.split('://');
      let baseUrl: string;
      if (urlSegments.length > 1)
        baseUrl = urlSegments[1];
      else baseUrl = `${location.host}${location.pathname}`;

      const url = `${protocol}://${baseUrl}/ws/`;
      logger.debug(`preparing to connect to ${url}`);
      const ws = new WebSocket(url);
      set(connection, ws);
      ws.onmessage = async (event): Promise<void> => handleMessage(event.data);
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
        if (!event.wasClean)
          startPromise(reconnect());
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

  /**
   * Enable or disable websocket connections.
   * When disabled, connect() and reconnect() will not attempt to connect.
   * Use this when the backend is known to be unavailable (e.g., startup error).
   */
  function setConnectionEnabled(enabled: boolean): void {
    set(connectionEnabled, enabled);
    if (!enabled) {
      logger.debug('Websocket connections disabled');
      disconnect();
    }
    else {
      logger.debug('Websocket connections enabled');
    }
  }

  return {
    connect,
    connected,
    disconnect,
    setConnectionEnabled,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useWebsocketStore, import.meta.hot));
