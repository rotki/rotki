import { createCustomPinia } from '@test/utils/create-pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mockConnect = vi.fn();
const mockDisconnect = vi.fn();
const mockConnected = ref<boolean>(false);

const mockMonitor = vi.fn();
const mockCheck = vi.fn();
const mockConsume = vi.fn();
const mockAutoRefresh = vi.fn();
const mockFetchTransactionStatusSummary = vi.fn();
const mockCheckIfPasswordConfirmationNeeded = vi.fn();

vi.mock('@/modules/shell/sync-progress/use-monitor-watchers', () => ({
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
  useWebsocketConnection: vi.fn((): { connect: typeof mockConnect; connected: typeof mockConnected; disconnect: typeof mockDisconnect } => ({
    connect: mockConnect,
    connected: mockConnected,
    disconnect: mockDisconnect,
  })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: {
    debug: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  },
}));

async function loadMonitorService(): Promise<typeof import('@/modules/shell/app/use-monitor-service')> {
  vi.doUnmock('@/modules/shell/app/use-monitor-service');
  vi.resetModules();
  return import('@/modules/shell/app/use-monitor-service');
}

describe('useMonitorService', () => {
  let service: ReturnType<typeof import('@/modules/shell/app/use-monitor-service').useMonitorService>;
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

    const { useMonitorService } = await loadMonitorService();
    scope.run(() => {
      service = useMonitorService();
    });
  });

  afterEach(() => {
    service.stop();
    scope.stop();
    vi.useRealTimers();
  });

  it('should call connect and set up intervals on start', async () => {
    service.start();

    await vi.advanceTimersByTimeAsync(0);

    expect(mockConnect).toHaveBeenCalledOnce();
    // check() is gated by canRequestData (false by default), so not called
    // monitor() is called immediately when not restarting
    expect(mockMonitor).toHaveBeenCalledOnce();
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

  it('should stop and then start with restarting=true on restart', async () => {
    service.start();
    await vi.advanceTimersByTimeAsync(0);

    vi.clearAllMocks();
    mockConnect.mockResolvedValue(undefined);

    service.restart();
    await vi.advanceTimersByTimeAsync(0);

    expect(mockDisconnect).toHaveBeenCalledOnce();
    expect(mockConnect).toHaveBeenCalledOnce();

    // Since restarting=true, fetch and monitor should NOT be called immediately
    expect(mockCheck).not.toHaveBeenCalled();
    expect(mockMonitor).not.toHaveBeenCalled();
  });

  it('should set up task monitoring interval via startTaskMonitoring', async () => {
    service.startTaskMonitoring(false);

    expect(mockMonitor).toHaveBeenCalledOnce();

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
