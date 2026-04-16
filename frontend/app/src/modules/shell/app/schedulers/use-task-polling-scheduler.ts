import { useTaskMonitor } from '@/modules/core/tasks/use-task-monitor';
import { useIntervalScheduler } from './use-interval-scheduler';

const TASK_POLLING_MS = 4_000;

interface UseTaskPollingSchedulerReturn {
  start: (immediate: boolean) => void;
  stop: () => void;
}

export function useTaskPollingScheduler(): UseTaskPollingSchedulerReturn {
  const { monitor } = useTaskMonitor();
  const scheduler = useIntervalScheduler({ callback: monitor, intervalMs: TASK_POLLING_MS });

  return {
    start: (immediate: boolean): void => scheduler.start(immediate),
    stop: scheduler.stop,
  };
}
