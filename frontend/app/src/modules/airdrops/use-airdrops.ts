import type { Ref } from 'vue';
import { map as mapResult, type Result } from 'plainfp/result';
import { Airdrops } from '@/modules/airdrops/airdrops';
import { useDefiApi } from '@/modules/airdrops/use-defi-api';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { ActivityKind, makeActivityId, useNativeTask } from '@/modules/task-center/use-native-task';

interface UseAirdropsReturn {
  airdrops: Readonly<Ref<Airdrops>>;
  loading: Readonly<Ref<boolean>>;
  fetchAirdrops: () => Promise<void>;
}

export function useAirdrops(): UseAirdropsReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { submitTask } = useNativeTask();
  const { notifyError } = useNotifications();
  const { fetchAirdrops: fetchAirdropsCaller } = useDefiApi();

  const airdrops = ref<Airdrops>({});
  const loading = shallowRef<boolean>(false);

  const fetchAirdrops = async (): Promise<void> => {
    set(loading, true);

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.AIRDROPS),
      kind: ActivityKind.AIRDROPS,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<Airdrops>(
          async () => fetchAirdropsCaller(),
        ),
        (result) => {
          set(airdrops, Airdrops.parse(result));
        },
      ),
      title: t('task_center.group.airdrops'),
    });

    onActionableError(outcome, (error) => {
      logger.error(error.message);
      notifyError(
        t('actions.defi.airdrops.error.title'),
        t('actions.defi.airdrops.error.description', {
          error: error.message,
        }),
      );
    });

    set(loading, false);
  };

  return {
    airdrops: shallowReadonly(airdrops),
    fetchAirdrops,
    loading: readonly(loading),
  };
}
