import type { SessionMonitor } from '@/modules/shell/app/use-session-monitor';
import { createCustomPinia } from '@test/utils/create-pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useMainStore } from '@/modules/core/common/use-main-store';

const mockConnect = vi.fn();
const mockDisconnect = vi.fn();
const mockSetConnectionEnabled = vi.fn();
const mockConnected = ref<boolean>(false);

const mockMonitor = vi.fn();
const mockCheck = vi.fn();
const mockConsume = vi.fn();
const mockAutoRefresh = vi.fn();
const mockFetchTransactionStatusSummary = vi.fn();
const mockCheckIfPasswordConfirmationNeeded = vi.fn();

vi.mock('@/modules/shell/app/use-monitor-watchers', () => ({
  useMonitorWatchers: vi.fn(),
}));

vi.mock('@/modules/auth/use-password-confirmation', () => ({
  usePasswordConfirmation: vi.fn((): { checkIfPasswordConfirmationNeeded: typeof mockCheckIfPasswordConfirmationNeeded } => ({
    checkIfPasswordConfirmationNeeded: mockCheckIfPasswordConfirmationNeeded,
  })),
}));

vi.mock('@/modules/balances/blockchain/use-token-detection-orchestrator', () => ({
  useTokenDetectionOrchestrator: vi.fn(),
}));

vi.mock('@/modules/balances/use-balance-fetching', () => ({
  useBalanceFetching: vi.fn((): { autoRefresh: typeof mockAutoRefresh } => ({
    autoRefresh: mockAutoRefresh,
  })),
}));

vi.mock('@/modules/history/use-history-data-fetching', () => ({
  useHistoryDataFetching: vi.fn((): { fetchTransactionStatusSummary: typeof mockFetchTransactionStatusSummary } => ({
    fetchTransactionStatusSummary: mockFetchTransactionStatusSummary,
  })),
}));

vi.mock('@/modules/core/messaging', () => ({
  useMessageHandling: vi.fn((): { consume: typeof mockConsume } => ({
    consume: mockConsume,
  })),
}));

vi.mock('@/modules/session/use-periodic-data-fetcher', () => ({
  usePeriodicDataFetcher: vi.fn((): { check: typeof mockCheck } => ({
    check: mockCheck,
  })),
}));

vi.mock('@/modules/core/tasks/use-task-monitor', () => ({
  useTaskMonitor: vi.fn((): { monitor: typeof mockMonitor } => ({
    monitor: mockMonitor,
  })),
}));

vi.mock('@/modules/shell/app/use-websocket-connection', () => ({
  useWebsocketConnection: vi.fn((): { connect: typeof mockConnect; connected: typeof mockConnected; disconnect: typeof mockDisconnect; setConnectionEnabled: typeof mockSetConnectionEnabled } => ({
    connect: mockConnect,
    connected: mockConnected,
    disconnect: mockDisconnect,
    setConnectionEnabled: mockSetConnectionEnabled,
  })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  getDefaultLogLevel: vi.fn(() => 'debug'),
  logger: {
    debug: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  },
  setLevel: vi.fn(),
}));

describe('useSessionMonitor', () => {
  let service: SessionMonitor;
  let scope: ReturnType<typeof effectScope>;

  beforeEach(async () => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    scope = effectScope();
    set(mockConnected, false);
    mockConnect.mockResolvedValue(undefined);
    mockMonitor.mockResolvedValue(undefined);
    mockCheck.mockResolvedValue(undefined);
    mockConsume.mockResolvedValue(undefined);
    mockAutoRefresh.mockResolvedValue(undefined);
    mockFetchTransactionStatusSummary.mockResolvedValue(undefined);
    mockCheckIfPasswordConfirmationNeeded.mockResolvedValue(undefined);

    setActivePinia(createCustomPinia());
    useMainStore().setConnected(true);

    vi.resetModules();
    const { useSessionMonitor } = await import('@/modules/shell/app/use-session-monitor');
    const built = scope.run(() => useSessionMonitor());
    assert(built);
    service = built;
  });

  afterEach(() => {
    scope.stop();
    vi.useRealTimers();
  });

  it('should call connect and set up intervals on start', async () => {
    service.start();

    await vi.advanceTimersByTimeAsync(0);

    expect(mockConnect).toHaveBeenCalledOnce();
    expect(mockMonitor).toHaveBeenCalledOnce();
  });

  it('should re-arm websocket reconnection on start', async () => {
    service.start();
    await vi.advanceTimersByTimeAsync(0);

    expect(mockSetConnectionEnabled).toHaveBeenCalledWith(true);
  });

  it('should disable websocket reconnection on stop (not just close the socket)', async () => {
    service.start();
    await vi.advanceTimersByTimeAsync(0);
    vi.clearAllMocks();

    service.stop();

    expect(mockSetConnectionEnabled).toHaveBeenCalledWith(false);
    expect(mockDisconnect).toHaveBeenCalledOnce();
  });

  it('should call disconnect and clear all intervals on stop', async () => {
    service.start();
    await vi.advanceTimersByTimeAsync(0);

    vi.clearAllMocks();

    service.stop();

    expect(mockDisconnect).toHaveBeenCalledOnce();

    await vi.advanceTimersByTimeAsync(60_000);

    expect(mockCheck).not.toHaveBeenCalled();
    expect(mockMonitor).not.toHaveBeenCalled();
  });

  it('should stop polling and close the socket when its scope is disposed', async () => {
    service.start();
    await vi.advanceTimersByTimeAsync(0);
    vi.clearAllMocks();

    scope.stop();

    expect(mockSetConnectionEnabled).toHaveBeenCalledWith(false);
    expect(mockDisconnect).toHaveBeenCalledOnce();

    await vi.advanceTimersByTimeAsync(60_000);

    expect(mockConsume).not.toHaveBeenCalled();
    expect(mockCheck).not.toHaveBeenCalled();
    expect(mockMonitor).not.toHaveBeenCalled();
  });

  it('should keep polling tasks on an interval once started', async () => {
    service.start();
    await vi.advanceTimersByTimeAsync(0);
    vi.clearAllMocks();
    mockMonitor.mockResolvedValue(undefined);

    await vi.advanceTimersByTimeAsync(4_000);

    expect(mockMonitor).toHaveBeenCalledOnce();
  });

  it('should not call fetch/monitor immediately when restarting is true', async () => {
    service.start(true);
    await vi.advanceTimersByTimeAsync(0);

    expect(mockConnect).toHaveBeenCalledOnce();
    expect(mockCheck).not.toHaveBeenCalled();
    expect(mockConsume).not.toHaveBeenCalled();
    expect(mockMonitor).not.toHaveBeenCalled();

    mockMonitor.mockResolvedValue(undefined);
    await vi.advanceTimersByTimeAsync(4_000);
    expect(mockMonitor).toHaveBeenCalledOnce();
  });
});
