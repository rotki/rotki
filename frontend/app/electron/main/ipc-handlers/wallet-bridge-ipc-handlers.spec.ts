// @vitest-environment node
import type { LogService } from '@electron/main/log-service';
import type { WalletBridgeWebSocketServer } from '@electron/main/ws';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { WalletBridgeIpcHandlers } from './wallet-bridge-ipc-handlers';

const { appServer, openExternal } = vi.hoisted(() => ({
  appServer: {
    isListening: vi.fn<() => boolean>(),
    start: vi.fn<(port: number) => Promise<void>>(),
    stop: vi.fn<() => void>(),
  },
  openExternal: vi.fn<(url: string) => Promise<void>>(),
}));

vi.mock('electron', () => ({ shell: { openExternal } }));

vi.mock('@electron/main/app-server', () => ({
  AppServer: class {
    isListening = appServer.isListening;
    start = appServer.start;
    stop = appServer.stop;
  },
}));

vi.mock('@shared/port-utils', () => ({
  selectPort: vi.fn<(port: number) => Promise<number>>(async port => port + (appServer.isListening() ? 1 : 0)),
}));

describe('electron/main/ipc-handlers/wallet-bridge-ipc-handlers', () => {
  const start = vi.fn<(port: number) => Promise<void>>();
  const disconnect = vi.fn<() => void>();
  let wsListening = false;
  let handlers: WalletBridgeIpcHandlers;

  beforeEach(() => {
    vi.clearAllMocks();
    wsListening = false;
    let httpListening = false;
    appServer.isListening.mockImplementation(() => httpListening);
    appServer.start.mockImplementation(async () => {
      httpListening = true;
    });
    appServer.stop.mockImplementation(() => {
      httpListening = false;
    });
    start.mockImplementation(async () => {
      wsListening = true;
    });
    handlers = new WalletBridgeIpcHandlers(
      createMock<LogService>({ debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() }),
      createMock<WalletBridgeWebSocketServer>({
        disconnect,
        isConnected: () => false,
        isListening: () => wsListening,
        start,
      }),
    );
  });

  it('should restart only the websocket server, on the same port, after an idle timeout', async () => {
    await handlers.openWalletConnectBridge();
    wsListening = false;
    vi.clearAllMocks();

    await handlers.openWalletConnectBridge();

    expect(start).toHaveBeenCalledExactlyOnceWith(40011);
    expect(appServer.start).not.toHaveBeenCalled();
    expect(openExternal).toHaveBeenCalledExactlyOnceWith('http://localhost:40010/#/wallet-bridge');
  });

  it('should start a fresh pair when the websocket server cannot come back on its port', async () => {
    await handlers.openWalletConnectBridge();
    wsListening = false;
    vi.clearAllMocks();
    start.mockRejectedValueOnce(new Error('EADDRINUSE'));

    await handlers.openWalletConnectBridge();

    expect(appServer.stop).toHaveBeenCalledTimes(1);
    expect(appServer.start).toHaveBeenCalledTimes(1);
    expect(openExternal).toHaveBeenCalledTimes(1);
  });

  it('should start both servers on the first open', async () => {
    await handlers.openWalletConnectBridge();

    expect(appServer.start).toHaveBeenCalledWith(40010, '/#/wallet-bridge');
    expect(start).toHaveBeenCalledWith(40011);
  });
});
