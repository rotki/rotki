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
  const confirmStore = useConfirmStore();
  const { dismiss, show } = confirmStore;
  const { confirmation, visible } = storeToRefs(confirmStore);

  function confirmCancel(activity: Activity): void {
    const live = computed<boolean>(() => get(activities)
      .some(item => item.id === activity.id && !isTerminalStatus(item.status)));

    // Every exit runs through `stop`, and there are three of them, because a watcher created here
    // belongs to no component scope: one that outlives its dialog is never collected, and would go
    // on calling `dismiss()` at every later settle, closing whatever confirmation happened to be
    // open at the time.
    //
    // 1. `done` covers the debounce timer. Unwatching does not unschedule an already pending
    //    `dismissWhenSettled`, so a user who acts inside the debounce window would still get a
    //    `dismiss()` a second later, aimed at whatever dialog is open by then.
    // 2. `unwatchOwnership` covers being superseded. `useConfirmStore` is a single global slot, so
    //    any other `show()` overwrites the dismiss handler below and our own `stop` never runs.
    const stops: (() => void)[] = [];
    let done = false;
    const stop = (): void => {
      done = true;
      for (const off of stops.splice(0))
        off();
    };

    // Debounced: a settle emits more than once in quick succession (the status, then the ledger
    // write), and the dialog should not blink shut on the first of them.
    const dismissWhenSettled = useDebounceFn(async () => {
      if (done)
        return;

      stop();
      await dismiss();
    }, 1000);

    // `immediate`, because the work can already be terminal by the time the row is clicked — the
    // snapshot the row rendered from is one tick old. Without it `live` starts false, never
    // transitions, and the dialog sits there asking to cancel something already finished.
    stops.push(watch(live, (isLive) => {
      if (!isLive)
        startPromise(dismissWhenSettled());
    }, { immediate: true }));

    const message = {
      message: t('collapsed_pending_tasks.cancel_task_info', {
        title: resolveText(t, activity.subtitle) ?? activity.title,
      }),
      title: t('collapsed_pending_tasks.cancel_task'),
      type: 'warning' as const,
    };

    // The slot is ours only until someone else claims it; identity, not visibility, is what says so.
    // ⚠️ `toRaw` is load-bearing: the store holds the message in a plain `ref`, which deeply
    // reactifies it, so `get(confirmation)` is a proxy *of* `message` and never `message` itself.
    // Comparing them directly is always unequal — it stopped the self-dismiss the instant the
    // dialog opened, disabling the whole composable.
    stops.push(watch([visible, confirmation], ([shown, current]) => {
      if (!shown || toRaw(current) !== message)
        stop();
    }));

    show(message, async () => {
      stop();
      await cancel(activity);
    }, stop);
  }

  return { confirmCancel };
}
