import type { QueueState } from './types';
import { get } from '@vueuse/shared';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { reactive } from 'vue';
import { useRequestQueueState } from './use-request-queue-state';

const mockQueueState = reactive<QueueState>({
  active: 0,
  highPriorityQueued: 0,
  isOverloaded: false,
  queued: 0,
  requestsThisSecond: 0,
});

vi.mock('../rotki-api', () => ({
  api: {
    get queueState(): QueueState {
      return mockQueueState;
    },
  },
}));

vi.mock('vue-i18n', () => ({
  useI18n: (): { t: (key: string, params?: { active?: number; queued?: number }) => string } => ({
    t: (key: string, params?: { active?: number; queued?: number }): string => {
      const active = params?.active ?? 0;
      const queued = params?.queued ?? 0;
      if (key === 'request_queue.loading_active_and_queued')
        return `Loading (${active} active, ${queued} queued)`;
      if (key === 'request_queue.loading_active')
        return `Loading (${active} active)`;
      if (key === 'request_queue.loading_queued')
        return `Loading (${queued} queued)`;
      return key;
    },
  }),
}));

describe('useRequestQueueState', () => {
  beforeEach(() => {
    mockQueueState.active = 0;
    mockQueueState.queued = 0;
    mockQueueState.highPriorityQueued = 0;
    mockQueueState.isOverloaded = false;
    mockQueueState.requestsThisSecond = 0;
  });

  describe('isLoading', () => {
    it('returns false when no requests are active or queued', () => {
      const { isLoading } = useRequestQueueState();

      expect(get(isLoading)).toBe(false);
    });

    it('returns true when requests are active', () => {
      mockQueueState.active = 3;

      const { isLoading } = useRequestQueueState();

      expect(get(isLoading)).toBe(true);
    });

    it('returns true when requests are queued', () => {
      mockQueueState.queued = 5;

      const { isLoading } = useRequestQueueState();

      expect(get(isLoading)).toBe(true);
    });

    it('returns true when both active and queued', () => {
      mockQueueState.active = 2;
      mockQueueState.queued = 3;

      const { isLoading } = useRequestQueueState();

      expect(get(isLoading)).toBe(true);
    });
  });

  describe('loadingMessage', () => {
    it('returns empty string when no requests', () => {
      const { loadingMessage } = useRequestQueueState();

      expect(get(loadingMessage)).toBe('');
    });

    it('shows only active count when no queued requests', () => {
      mockQueueState.active = 3;

      const { loadingMessage } = useRequestQueueState();

      expect(get(loadingMessage)).toBe('Loading (3 active)');
    });

    it('shows only queued count when no active requests', () => {
      mockQueueState.queued = 5;

      const { loadingMessage } = useRequestQueueState();

      expect(get(loadingMessage)).toBe('Loading (5 queued)');
    });

    it('shows both active and queued counts', () => {
      mockQueueState.active = 2;
      mockQueueState.queued = 8;

      const { loadingMessage } = useRequestQueueState();

      expect(get(loadingMessage)).toBe('Loading (2 active, 8 queued)');
    });
  });

  describe('totalPending', () => {
    it('returns 0 when no requests', () => {
      const { totalPending } = useRequestQueueState();

      expect(get(totalPending)).toBe(0);
    });

    it('returns sum of active and queued', () => {
      mockQueueState.active = 3;
      mockQueueState.queued = 7;

      const { totalPending } = useRequestQueueState();

      expect(get(totalPending)).toBe(10);
    });
  });

  describe('state', () => {
    it('returns the reactive queue state', () => {
      mockQueueState.active = 5;
      mockQueueState.queued = 10;
      mockQueueState.highPriorityQueued = 2;
      mockQueueState.isOverloaded = true;
      mockQueueState.requestsThisSecond = 15;

      const { state } = useRequestQueueState();

      expect(state.active).toBe(5);
      expect(state.queued).toBe(10);
      expect(state.highPriorityQueued).toBe(2);
      expect(state.isOverloaded).toBe(true);
      expect(state.requestsThisSecond).toBe(15);
    });

    it('reflects state changes reactively', () => {
      const { state, isLoading, totalPending } = useRequestQueueState();

      expect(get(isLoading)).toBe(false);
      expect(get(totalPending)).toBe(0);

      mockQueueState.active = 3;
      mockQueueState.queued = 2;

      expect(state.active).toBe(3);
      expect(state.queued).toBe(2);
      expect(get(isLoading)).toBe(true);
      expect(get(totalPending)).toBe(5);
    });
  });
});
