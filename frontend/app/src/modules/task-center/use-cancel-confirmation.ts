import { startPromise } from '@shared/utils';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { isTerminalStatus } from './core/status';
import { type Activity, resolveText } from './core/types';
import { useTaskController } from './use-task-controller';
import { useTaskOrchestrator } from './use-task-orchestrator';

interface UseCancelConfirmationReturn {
  confirmCancel: (activity: Activity) => void;
}

/**
 * Asks before cancelling an activity, and gets out of the way if the work settles first.
 *
 * The self-dismiss is the whole reason this is not two lines in the component: the dialog names
 * one activity, and work in a task panel finishes on its own schedule. Leaving it up asks the user
 * to confirm cancelling something that already completed, and confirming it would then cancel
 * nothing — `orchestrator.cancel` refuses a terminal id.
 */
export function useCancelConfirmation(): UseCancelConfirmationReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { activities } = useTaskOrchestrator();
  const { cancel } = useTaskController();
  const { dismiss, show } = useConfirmStore();

  function confirmCancel(activity: Activity): void {
    const live = computed<boolean>(() => get(activities)
      .some(item => item.id === activity.id && !isTerminalStatus(item.status)));

    // Every exit runs through `stop`, including the self-dismiss below. A watcher created here
    // belongs to no component scope, so one that outlives its dialog is never collected: it would
    // go on calling `dismiss()` on every later settle, closing whatever confirmation happened to
    // be open at the time.
    //
    // `done` closes the same hole on the debounce timer. Unwatching does not unschedule an already
    // pending `dismissWhenSettled`, so a user who confirms or backs out inside the debounce window
    // would still get a `dismiss()` a second later — aimed at whatever dialog is open by then, not
    // at this one.
    let unwatch: () => void = () => {};
    let done = false;
    const stop = (): void => {
      done = true;
      unwatch();
    };

    // Debounced: a settle emits more than once in quick succession (the status, then the ledger
    // write), and the dialog should not blink shut on the first of them.
    const dismissWhenSettled = useDebounceFn(async () => {
      if (done)
        return;

      stop();
      await dismiss();
    }, 1000);

    unwatch = watch(live, (isLive) => {
      if (!isLive)
        startPromise(dismissWhenSettled());
    });

    show(
      {
        message: t('collapsed_pending_tasks.cancel_task_info', {
          title: resolveText(t, activity.subtitle) ?? activity.title,
        }),
        title: t('collapsed_pending_tasks.cancel_task'),
        type: 'warning',
      },
      async () => {
        stop();
        await cancel(activity);
      },
      stop,
    );
  }

  return { confirmCancel };
}
