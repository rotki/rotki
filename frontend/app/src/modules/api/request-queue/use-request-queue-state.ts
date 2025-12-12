import type { QueueState } from './types';
import { computed, type ComputedRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../rotki-api';

interface UseRequestQueueStateReturn {
  /** True if any requests are active or queued */
  isLoading: ComputedRef<boolean>;
  /** Human-readable loading message */
  loadingMessage: ComputedRef<string>;
  /** Reactive queue state */
  state: QueueState;
  /** Total number of pending requests (queued + active) */
  totalPending: ComputedRef<number>;
}

/**
 * Composable that provides reactive access to the request queue state.
 * Use this in components to show loading indicators and queue status.
 */
export function useRequestQueueState(): UseRequestQueueStateReturn {
  const { t } = useI18n({ useScope: 'global' });
  const state = api.queueState;

  const isLoading = computed<boolean>(() => state.active > 0 || state.queued > 0);

  const loadingMessage = computed<string>(() => {
    const total = state.active + state.queued;
    if (total === 0)
      return '';
    if (state.active > 0 && state.queued > 0)
      return t('request_queue.loading_active_and_queued', { active: state.active, queued: state.queued });
    if (state.active > 0)
      return t('request_queue.loading_active', { active: state.active });
    return t('request_queue.loading_queued', { queued: state.queued });
  });

  const totalPending = computed<number>(() => state.queued + state.active);

  return {
    /** True if any requests are active or queued */
    isLoading,
    /** Human-readable loading message */
    loadingMessage,
    /** Reactive queue state */
    state,
    /** Total number of pending requests (queued + active) */
    totalPending,
  };
}
