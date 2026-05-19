import { beforeEach, describe, expect, it } from 'vitest';
import { useBridgeLogging } from '@/modules/wallet/bridge/use-bridge-logging';

describe('useBridgeLogging', () => {
  beforeEach(() => {
    // useBridgeLogging is a shared composable; reset state between tests
    const { clearLogs } = useBridgeLogging();
    clearLogs();
  });

  it('should start with an empty log list', () => {
    const { logs } = useBridgeLogging();
    expect(get(logs)).toEqual([]);
  });

  it('should default the log type to info', () => {
    const { addLog, logs } = useBridgeLogging();
    addLog('hello');
    expect(get(logs)).toHaveLength(1);
    expect(get(logs)[0].type).toBe('info');
    expect(get(logs)[0].message).toBe('hello');
    expect(typeof get(logs)[0].timestamp).toBe('string');
  });

  it('should prepend new entries so the latest log is first', () => {
    const { addLog, logs } = useBridgeLogging();
    addLog('first', 'info');
    addLog('second', 'success');
    addLog('third', 'error');

    expect(get(logs).map(l => l.message)).toEqual(['third', 'second', 'first']);
    expect(get(logs).map(l => l.type)).toEqual(['error', 'success', 'info']);
  });

  it('should clear all entries', () => {
    const { addLog, clearLogs, logs } = useBridgeLogging();
    addLog('a');
    addLog('b');
    expect(get(logs)).toHaveLength(2);

    clearLogs();
    expect(get(logs)).toEqual([]);
  });

  it('should share state across calls (shared composable)', () => {
    const first = useBridgeLogging();
    first.addLog('shared');

    const second = useBridgeLogging();
    expect(get(second.logs)).toHaveLength(1);
    expect(get(second.logs)[0].message).toBe('shared');
  });
});
