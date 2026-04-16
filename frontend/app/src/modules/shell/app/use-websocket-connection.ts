import type { Ref } from 'vue';
import { startPromise } from '@shared/utils';
import { api } from '@/modules/core/api/rotki-api';
import { delay } from '@/modules/core/common/async/async-utilities';
import { logger } from '@/modules/core/common/logging/logging';
import { useMessageHandling } from '@/modules/core/messaging';

/** Delay in milliseconds before attempting to reconnect to websocket */
const RECONNECT_DELAY_MS = 2000;

interface UseWebsocketConnectionInternalReturn {
  connect: () => Promise<boolean>;
  connected: Readonly<Ref<boolean>>;
  disconnect: () => void;
  setConnectionEnabled: (enabled: boolean) => void;
}

function isSecureConnection(serverUrl: string): boolean {
  const location = typeof window !== 'undefined' ? window.location : undefined;
  return serverUrl.startsWith('https') || !!location?.protocol.startsWith('https');
}

function resolveBaseUrl(serverUrl: string): string {
  const urlSegments = serverUrl.split('://');
  if (urlSegments.length > 1)
    return urlSegments[1];

  const location = typeof window !== 'undefined' ? window.location : undefined;
  return `${location?.host ?? ''}${location?.pathname ?? ''}`;
}

function buildWebsocketUrl(): string {
  const serverUrl = api.serverUrl;
  const protocol = isSecureConnection(serverUrl) ? 'wss' : 'ws';
  const baseUrl = resolveBaseUrl(serverUrl);
  return `${protocol}://${baseUrl}/ws/`;
}

interface WebSocketCallbacks {
  onClose: (event: CloseEvent) => void;
  onError: () => void;
  onMessage: (event: MessageEvent) => void;
  onOpen: () => void;
}

function createWebSocket(url: string, callbacks: WebSocketCallbacks): WebSocket {
  const ws = new WebSocket(url);
  ws.onmessage = callbacks.onMessage;
  ws.onerror = callbacks.onError;
  ws.addEventListener('open', callbacks.onOpen);
  ws.addEventListener('close', callbacks.onClose);
  return ws;
}

function useWebsocketConnectionInternal(): UseWebsocketConnectionInternalReturn {
  const connection = shallowRef<WebSocket>();
  const connected = shallowRef<boolean>(false);
  /** When false, connection attempts are blocked (e.g., backend failed to start) */
  const connectionEnabled = shallowRef<boolean>(true);

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
    catch (error: unknown) {
      logger.debug(error, 'Reconnect failed');
    }
  };

  async function connect(): Promise<boolean> {
    if (!get(connectionEnabled)) {
      logger.debug('Websocket connection skipped - connection disabled');
      return false;
    }
    if (get(connected))
      return true;

    const existing = get(connection);
    if (existing) {
      logger.debug('closing stale websocket before reconnect');
      existing.close();
    }

    const url = buildWebsocketUrl();
    logger.debug(`preparing to connect to ${url}`);

    return new Promise<boolean>((resolve) => {
      const ws = createWebSocket(url, {
        onClose(event: CloseEvent): void {
          logger.debug('websocket connection closed');
          set(connected, false);
          if (!event.wasClean)
            startPromise(reconnect());
        },
        onError(): void {
          logger.error('websocket connection failed');
          set(connected, false);
          resolve(false);
        },
        onMessage: (event: MessageEvent): void => {
          startPromise(handleMessage(event.data));
        },
        onOpen(): void {
          logger.debug('websocket connected');
          set(connected, true);
          resolve(true);
        },
      });
      set(connection, ws);
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

  onScopeDispose(() => {
    disconnect();
  });

  return {
    connect,
    connected: readonly(connected),
    disconnect,
    setConnectionEnabled,
  };
}

export const useWebsocketConnection = createGlobalState(useWebsocketConnectionInternal);
