import type { BankConnectionIdentity } from '@/modules/banks/types';
import type { ActivityId } from '@/modules/task-center/core/types';
import { toSentenceCase } from '@rotki/common';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useBanksApi } from '@/modules/banks/use-banks-api';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, isCancellation, type TaskError } from '@/modules/core/tasks/task-result';
import { bankEventsActivity } from '@/modules/history/events/tx/sync-activity';
import { useEventsQueryStatusStore } from '@/modules/history/use-events-query-status-store';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseBankEventsRefreshReturn {
  /** One outcome per bank connection, so the caller's umbrella can settle on what actually ran. */
  queryAllBankEvents: (banks: BankConnectionIdentity[], parent?: ActivityId) => Promise<Result<void, TaskError>[]>;
}

/**
 * Pulls new transactions of bank connections into the history.
 *
 * @remarks
 * Each `{ location, name }` connection runs as its own native BANK_EVENTS activity, the way exchange
 * accounts do, so the orchestrator owns liveness, cancellation and re-run, and the same status
 * frames the backend streams for exchanges drive its detail.
 */
export function useBankEventsRefresh(): UseBankEventsRefreshReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();
  const { markLocationCancelled } = useEventsQueryStatusStore();
  const { syncBanks } = useBanksApi();
  const { submitTask } = useNativeTask();

  const queryBank = async (bank: BankConnectionIdentity, parent?: ActivityId): Promise<Result<void, TaskError>> => {
    const { location, name } = bank;
    logger.debug(`querying bank events for ${location} (${name})`);
    const outcome = await submitTask({
      id: bankEventsActivity.id(bank),
      kind: bankEventsActivity.kind,
      lane: bankEventsActivity.laneOf?.(bank),
      parent,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<boolean>(async () => syncBanks({ location, name })),
        () => {},
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.history_events.bank'), { account: name, bank: toSentenceCase(location) }),
      title: t('task_center.group.bank_events'),
    });

    if (isErr(outcome)) {
      if (isCancellation(outcome.error)) {
        markLocationCancelled({ location, name });
      }
      else if (isActionable(outcome.error)) {
        logger.error(outcome.error);
        notifyError(
          t('actions.bank_events.error.title'),
          t('actions.bank_events.error.description', { error: outcome.error.message, location, name }),
        );
      }
    }

    return outcome;
  };

  /** Connections of one bank run in sequence and two banks at once; the lanes enforce that. */
  const queryAllBankEvents = async (banks: BankConnectionIdentity[], parent?: ActivityId): Promise<Result<void, TaskError>[]> =>
    Promise.all(banks.map(async bank => queryBank(bank, parent)));

  return {
    queryAllBankEvents,
  };
}
