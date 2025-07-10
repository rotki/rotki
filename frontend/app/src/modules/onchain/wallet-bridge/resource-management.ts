import { reactive } from 'vue';
import { logger } from '@/utils/logging';

export interface ResourceState {
  isSetupInProgress: boolean;
  setupAbortController: AbortController | null;
  setupTimeout: NodeJS.Timeout | null;
}

export function createResourceManager(): {
  resources: ResourceState;
  cleanupResources: () => void;
} {
  const resources = reactive<ResourceState>({
    isSetupInProgress: false,
    setupAbortController: null,
    setupTimeout: null,
  });

  function cleanupResources(): void {
    logger.debug('Cleaning up resources...');

    if (resources.setupAbortController && !resources.setupAbortController.signal.aborted) {
      logger.debug('Aborting ongoing setup');
      resources.setupAbortController.abort();
    }

    if (resources.setupTimeout) {
      clearTimeout(resources.setupTimeout);
      resources.setupTimeout = null;
    }

    resources.setupAbortController = null;
    resources.isSetupInProgress = false;

    logger.debug('Resources cleaned up successfully');
  }

  return {
    cleanupResources,
    resources,
  };
}
