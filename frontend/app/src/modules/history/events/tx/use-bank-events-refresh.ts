import type { BankConnectionIdentity } from '@/modules/banks/types';
import type { ActivityId } from '@/modules/task-center/core/types';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBanksApi } from '@/modules/banks/use-banks-api';
import { logger } from '@/modules/core/common/logging/logging';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { bankEventsActivity } from '@/modules/history/events/tx/sync.activity';
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
 * Each connection runs as its own native BANK_EVENTS activity, the way exchange
 * accounts do, so the orchestrator owns liveness, cancellation and re-run, and the same status
 * frames the backend streams for exchanges drive its detail.
 */
export function useBankEventsRefresh(): UseBankEventsRefreshReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { getBanks, syncBanks } = useBanksApi();
  const { submitTask } = useNativeTask();
  const store = useBankConnectionsStore();

  /**
   * Re-reads the connections, so what the syncs changed reaches the action center and the bank pages.
   *
   * @remarks
   * A sync the bank interrupts for a TAN finishes without a result or a message, which the task
   * layer cannot tell apart from a backend cancellation. The connection's sync status is the only
   * place the challenge is reported, and the action center's bank rows read it from the store.
   */
  const refreshConnections = async (): Promise<void> => {
    try {
      store.setConnections(await getBanks());
    }
    catch (error: unknown) {
      logger.error(error);
    }
  };

  const queryBank = async (bank: BankConnectionIdentity, parent?: ActivityId): Promise<Result<void, TaskError>> => {
    const { location, name } = bank;
    const bankName = store.bankNameFor(store.connectorOf(bank.identifier));
    logger.debug(`querying bank events for ${location} (${name})`);
    const outcome = await submitTask({
      id: bankEventsActivity.id(bank),
      kind: bankEventsActivity.kind,
      lane: bankEventsActivity.laneOf?.(bank),
      parent,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<boolean>(async () => syncBanks({ identifier: bank.identifier })),
        () => {},
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.history_events.bank'), { account: name, bank: bankName }),
      title: t('task_center.group.bank_events'),
    });

    if (isErr(outcome) && isActionable(outcome.error))
      logger.error(outcome.error);

    return outcome;
  };

  /**
   * Connections of one bank run in sequence and two banks at once; the lanes enforce that.
   *
   * @remarks
   * The connections are re-read once every sync has ended, whatever the outcome: a sync can raise,
   * clear or expire a challenge and record or clear a failure.
   */
  const queryAllBankEvents = async (banks: BankConnectionIdentity[], parent?: ActivityId): Promise<Result<void, TaskError>[]> => {
    const outcomes = await Promise.all(banks.map(async bank => queryBank(bank, parent)));
    if (banks.length > 0)
      await refreshConnections();
    return outcomes;
  };

  return {
    queryAllBankEvents,
  };
}
