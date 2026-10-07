import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { beginSession, endSession } from '@/modules/core/session/session-lifecycle';

interface FakeMonitor {
  start: Mock<(restarting?: boolean) => void>;
  stop: Mock<() => void>;
}

function fakeMonitor(): FakeMonitor {
  return { start: vi.fn(), stop: vi.fn() };
}

/**
 * Imports the facade into a fresh module registry.
 *
 * @remarks
 * `useMonitorService` is a `createGlobalState` singleton, so without the reset one test's hosted
 * monitor and wanted state would be the next one's. The shared setup mocks the facade for every
 * other spec, so this one unmocks it.
 */
async function setup(): Promise<ReturnType<typeof import('@/modules/shell/app/use-monitor-service')['useMonitorService']>> {
  vi.doUnmock('@/modules/shell/app/use-monitor-service');
  vi.resetModules();
  const { useMonitorService } = await import('@/modules/shell/app/use-monitor-service');
  return useMonitorService();
}

describe('modules/shell/app/use-monitor-service', () => {
  beforeEach(() => {
    beginSession();
  });

  it('should start the hosted monitor', async () => {
    const service = await setup();
    const monitor = fakeMonitor();
    service.host(monitor);

    service.start();

    expect(monitor.start).toHaveBeenCalledWith(false);
  });

  it('should apply a start asked for before the host built the monitor', async () => {
    const service = await setup();
    service.start(true);

    const monitor = fakeMonitor();
    service.host(monitor);

    expect(monitor.start).toHaveBeenCalledWith(true);
  });

  it('should not start a monitor hosted after a stop', async () => {
    const service = await setup();
    service.start();
    service.stop();

    const monitor = fakeMonitor();
    service.host(monitor);

    expect(monitor.start).not.toHaveBeenCalled();
  });

  it('should ignore a start with no session live, so it cannot carry into the next session', async () => {
    const service = await setup();
    endSession();
    service.start();

    beginSession();
    const monitor = fakeMonitor();
    service.host(monitor);

    expect(monitor.start).not.toHaveBeenCalled();
  });

  it('should forget a wanted start when the session ends', async () => {
    const service = await setup();
    service.start();

    beginSession();
    const monitor = fakeMonitor();
    service.host(monitor);

    expect(monitor.start).not.toHaveBeenCalled();
  });

  it('should drop the ended session\'s monitor at once, so a start before its host unmounts cannot reach it', async () => {
    const service = await setup();
    const ended = fakeMonitor();
    service.host(ended);

    beginSession();
    service.start();

    expect(ended.start).not.toHaveBeenCalled();
  });

  it('should restart by stopping, then starting without the immediate first poll', async () => {
    const service = await setup();
    const monitor = fakeMonitor();
    service.host(monitor);

    service.restart();

    expect(monitor.stop).toHaveBeenCalledOnce();
    expect(monitor.start).toHaveBeenCalledWith(true);
    expect(monitor.stop.mock.invocationCallOrder[0]).toBeLessThan(monitor.start.mock.invocationCallOrder[0]);
  });

  it('should only withdraw the monitor it hosted', async () => {
    const service = await setup();
    const first = fakeMonitor();
    const withdrawFirst = service.host(first);
    const second = fakeMonitor();
    service.host(second);

    withdrawFirst();
    service.start();

    expect(second.start).toHaveBeenCalledOnce();
    expect(first.start).not.toHaveBeenCalled();
  });
});
