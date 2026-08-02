import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import {
  type Activity,
  ActivityKind,
  ActivitySourceType,
  ActivityStatus,
  makeActivityId,
} from './core/types';
import { useTaskCenter } from './use-task-center';

const activities = ref<Activity[]>([]);

vi.mock('./use-task-orchestrator', () => ({
  useTaskOrchestrator: (): Record<string, unknown> => ({
    activities,
    useActivity: vi.fn(),
    useWorkStatus: vi.fn(),
    useWorkStatusPrefix: vi.fn(),
  }),
}));

function activity(status: ActivityStatus): Activity {
  return {
    cancellable: false,
    id: makeActivityId(ActivityKind.PRICES, status),
    kind: ActivityKind.PRICES,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status,
    title: 'prices',
  };
}

describe('useTaskCenter', () => {
  beforeEach(() => {
    activities.value = [];
  });

  describe('isActive', () => {
    it('should be false when there are no activities', () => {
      const { isActive } = useTaskCenter();
      expect(get(isActive)).toBe(false);
    });

    it('should be true while an activity is running', () => {
      activities.value = [activity(ActivityStatus.RUNNING)];
      const { isActive } = useTaskCenter();
      expect(get(isActive)).toBe(true);
    });

    it('should be true while an activity is queued', () => {
      activities.value = [activity(ActivityStatus.PENDING)];
      const { isActive } = useTaskCenter();
      expect(get(isActive)).toBe(true);
    });

    it('should be false once every activity has settled', () => {
      activities.value = [
        activity(ActivityStatus.COMPLETE),
        activity(ActivityStatus.FAILED),
        activity(ActivityStatus.CANCELLED),
      ];
      const { isActive } = useTaskCenter();
      expect(get(isActive)).toBe(false);
    });

    it('should stay true when only some activities have settled', () => {
      activities.value = [activity(ActivityStatus.COMPLETE), activity(ActivityStatus.RUNNING)];
      const { isActive } = useTaskCenter();
      expect(get(isActive)).toBe(true);
    });
  });
});
