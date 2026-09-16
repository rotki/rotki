import type { ComputedRef } from 'vue';
import { startPromise } from '@shared/utils';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { isTerminalStatus } from './core/status';
import { type Activity, resolveText } from './core/types';
import { useTaskController } from './use-task-controller';
import { useTaskOrchestrator } from './use-task-orchestrator';

interface UseCancelConfirmationReturn {
  confirmCancel: (activity: Activity) => void;
  /** Asks before stopping several jobs at once. */
  confirmCancelAll: (targets: Activity[], keptRunning: number) => void;
}

/**
 * Asks before cancelling, and gets out of the way if the work settles first.
 *
 * The self-dismiss is the whole reason this is not two lines in the component: work in a task panel
 * finishes on its own schedule. Leaving the dialog up asks the user to confirm cancelling something
 * that already completed, and confirming it would then cancel nothing, since `orchestrator.cancel`
 * refuses a terminal id.
 */
export function useCancelConfirmation(): UseCancelConfirmationReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { activities } = useTaskOrchestrator();
  const { cancel } = useTaskController();
  const confirmStore = useConfirmStore();
  const { dismiss, show } = confirmStore;
  const { confirmation, visible } = storeToRefs(confirmStore);

  /**
   * Shows `message`, runs `onConfirm` if accepted, and closes the dialog on its own once `live`
   * turns false.
   *
   * @remarks
   * The close is debounced because a settle emits more than once in quick succession (the status,
   * then the ledger write), and the dialog should not blink shut on the first of them.
   */
  function confirmWhileLive(
    message: { message: string; title: string; type: 'warning' },
    live: ComputedRef<boolean>,
    onConfirm: () => Promise<unknown>,
  ): void {
    const stops: (() => void)[] = [];
    let done = false;
    const stop = (): void => {
      done = true;
      for (const off of stops.splice(0))
        off();
    };

    const dismissWhenSettled = useDebounceFn(async () => {
      if (done)
        return;

      stop();
      await dismiss();
    }, 1000);

    stops.push(watch(live, (isLive) => {
      if (!isLive)
        startPromise(dismissWhenSettled());
    }, { immediate: true }));

    stops.push(watch([visible, confirmation], ([shown, current]) => {
      if (!shown || toRaw(current) !== message)
        stop();
    }));

    show(message, async () => {
      stop();
      await onConfirm();
    }, stop);
  }

  function confirmCancel(activity: Activity): void {
    const live = computed<boolean>(() => get(activities)
      .some(item => item.id === activity.id && !isTerminalStatus(item.status)));

    confirmWhileLive({
      message: t('collapsed_pending_tasks.cancel_task_info', {
        title: resolveText(t, activity.subtitle) ?? activity.title,
      }),
      title: t('collapsed_pending_tasks.cancel_task'),
      type: 'warning',
    }, live, async () => cancel(activity));
  }

  /**
   * Asks before stopping several jobs at once, naming how many stop and how many keep running.
   *
   * @param targets - the jobs to stop; each cancel cascades to its subtree
   * @param keptRunning - how many listed jobs are left running because stopping them is unsafe, said in the prompt so the user is not surprised that work goes on
   */
  function confirmCancelAll(targets: Activity[], keptRunning: number): void {
    const ids = new Set(targets.map(target => target.id));
    const live = computed<boolean>(() => get(activities)
      .some(item => ids.has(item.id) && !isTerminalStatus(item.status)));

    const stops = t('task_dock.panel.stop_all_info', { count: targets.length }, targets.length);
    const message = keptRunning > 0
      ? `${stops} ${t('task_dock.panel.stop_all_kept', { count: keptRunning }, keptRunning)}`
      : stops;

    confirmWhileLive({
      message,
      title: t('task_dock.panel.stop_all'),
      type: 'warning',
    }, live, async () => Promise.allSettled(targets.map(async target => cancel(target))));
  }

  return { confirmCancel, confirmCancelAll };
}
