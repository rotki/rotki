import type { Ref } from 'vue';

type LogType = 'info' | 'success' | 'error';

export interface LogEntry {
  message: string;
  timestamp: string;
  type: LogType;
}

interface BridgeLoggingComposable {
  addLog: (message: string, type?: 'info' | 'success' | 'error') => void;
  clearLogs: () => void;
  logs: Ref<LogEntry[]>;
}

function _useBridgeLogging(): BridgeLoggingComposable {
  const logs = ref<LogEntry[]>([]);

  const addLog = (message: string, type: 'info' | 'success' | 'error' = 'info'): void => {
    const timestamp = new Date().toLocaleTimeString();
    set(logs, [{ message, timestamp, type }, ...get(logs)]);
  };

  const clearLogs = (): void => {
    set(logs, []);
  };

  return {
    addLog,
    clearLogs,
    logs,
  };
}

export const useBridgeLogging = createSharedComposable(_useBridgeLogging);
