import type { ComputedRef } from 'vue';
import { startPromise } from '@shared/utils';
import { logger } from '@/utils/logging';

interface UseHealthCheckOptions {
  interval: number;
  onError?: (error: Error) => void;
}

interface UseHealthCheckReturn {
  start: (isConnected: () => boolean, onDisconnect: () => void) => void;
  stop: () => void;
  isActive: ComputedRef<boolean>;
}

// Composable for health check functionality
export function useHealthCheck(
  checkConnection: () => Promise<boolean>,
  options: UseHealthCheckOptions,
): UseHealthCheckReturn {
  const intervalRef = ref<NodeJS.Timeout>();
  const isActive = computed<boolean>(() => intervalRef.value !== undefined);

  const stop = (): void => {
    if (intervalRef.value) {
      clearInterval(intervalRef.value);
      intervalRef.value = undefined;
    }
  };

  const start = (isConnected: () => boolean, onDisconnect: () => void): void => {
    // Clear any existing interval
    stop();

    const performHealthCheck = async (): Promise<void> => {
      if (get(isActive) && isConnected()) {
        try {
          const connected = await checkConnection();
          if (!connected) {
            logger.debug('Health check detected disconnection');
            onDisconnect();
            stop();
          }
        }
        catch (error) {
          logger.error('Health check failed:', error);
          if (options.onError) {
            options.onError(error as Error);
          }
          onDisconnect();
          stop();
        }
      }
    };

    intervalRef.value = setInterval(() => {
      startPromise(performHealthCheck());
    }, options.interval);
  };

  // Cleanup on unmount
  onBeforeUnmount(stop);

  return {
    isActive,
    start,
    stop,
  };
}
