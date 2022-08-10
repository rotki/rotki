import { Severity } from '@rotki/common/lib/messages';
import { ref, watch } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore } from 'pinia';
import i18n from '@/i18n';
import { setupPremium } from '@/premium/setup-premium';
import { balanceKeys } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { SYNC_DOWNLOAD, SyncAction } from '@/services/types-api';
import { useDefiStore } from '@/store/defi';
import { useMainStore } from '@/store/main';
import { useNotifications } from '@/store/notifications';
import { PremiumCredentialsPayload } from '@/store/session/types';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export const usePremiumStore = defineStore('session/premium', () => {
  const premium = ref(false);
  const premiumSync = ref(false);
  const componentsLoaded = ref(false);

  const { isTaskRunning, awaitTask } = useTasks();
  const { notify } = useNotifications();

  const setup = async ({
    apiKey,
    apiSecret,
    username
  }: PremiumCredentialsPayload): Promise<ActionStatus> => {
    try {
      const success = await api.setPremiumCredentials(
        username,
        apiKey,
        apiSecret
      );

      if (success) {
        set(premium, true);
      }
      return { success };
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  };

  const deletePremium = async (): Promise<ActionStatus> => {
    try {
      const success = await api.deletePremiumCredentials();
      if (success) {
        set(premium, false);
      }
      return { success };
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  };

  async function forceSync(
    action: SyncAction,
    logout: () => Promise<void>
  ): Promise<void> {
    const taskType = TaskType.FORCE_SYNC;
    if (get(isTaskRunning(taskType))) {
      return;
    }

    try {
      const { taskId } = await api.forceSync(action);
      await awaitTask<boolean, TaskMeta>(taskId, taskType, {
        title: i18n.tc('actions.session.force_sync.task.title'),
        numericKeys: balanceKeys
      });
      const title = i18n.tc('actions.session.force_sync.success.title');
      const message = i18n.tc('actions.session.force_sync.success.message');

      notify({
        title,
        message,
        severity: Severity.INFO,
        display: true
      });

      if (action === SYNC_DOWNLOAD) {
        await logout();
      }
    } catch (e: any) {
      const title = i18n.tc('actions.session.force_sync.error.title');
      const message = i18n.tc('actions.session.force_sync.error.message', 0, {
        error: e.message
      });

      notify({
        title,
        message,
        display: true
      });
    }
  }

  const reset = () => {
    set(premium, false);
    set(premiumSync, false);
    set(componentsLoaded, false);
  };

  watch(premium, async (premium, prev) => {
    if (premium !== prev) {
      if (premium) {
        await setupPremium();
      }

      useDefiStore().reset();
      useMainStore().resetDefiStatus();
    }
  });

  return {
    premium,
    premiumSync,
    componentsLoaded,
    setup,
    deletePremium,
    forceSync,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(usePremiumStore, import.meta.hot));
}
