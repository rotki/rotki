import type { BankAuthChallenge, BankConnectionIdentity } from '@/modules/banks/types';
import type { ActivityId } from '@/modules/task-center/core/types';
import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { hasTag } from 'plainfp/tagged';
import { msg } from '@/message-key';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
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
  const { notify, notifyError } = useNotifications();
  const { markLocationCancelled } = useEventsQueryStatusStore();
  const { getBanks, syncBanks } = useBanksApi();
  const { submitTask } = useNativeTask();
  const store = useBankConnectionsStore();

  /**
   * The challenge a sync paused on, read from a fresh connection list.
   *
   * @remarks
   * A sync the bank interrupts for a TAN finishes without a result or a message, which the task
   * layer cannot tell apart from a backend cancellation. The connection's sync status is the only
   * place the challenge is reported.
   */
  const pendingChallenge = async ({ location, name }: BankConnectionIdentity): Promise<BankAuthChallenge | undefined> => {
    try {
      const connections = await getBanks();
      store.setConnections(connections);
      return connections.find(connection => connection.location === location && connection.name === name)?.syncStatus.authChallenge ?? undefined;
    }
    catch (error: unknown) {
      logger.error(error);
      return undefined;
    }
  };

  const notifyAuthenticationRequired = ({ location, name }: BankConnectionIdentity): void => {
    notify({
      action: {
        action: async () => {
          const { router } = await import('@/router');
          await router.push({ name: '/api-keys/banks/', query: { authenticate: name, location } });
        },
        icon: 'lu-shield-check',
        label: t('actions.bank_events.authentication.action'),
      },
      category: NotificationCategory.DEFAULT,
      message: t('actions.bank_events.authentication.description', { location: store.bankNameFor(location), name }),
      priority: Priority.ACTION,
      severity: Severity.WARNING,
      title: t('actions.bank_events.authentication.title'),
    });
  };

  const queryBank = async (bank: BankConnectionIdentity, parent?: ActivityId): Promise<Result<void, TaskError>> => {
    const { location, name } = bank;
    const bankName = store.bankNameFor(location);
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
      subtitle: activityLabelFor(msg.$t('task_center.activity.history_events.bank'), { account: name, bank: bankName }),
      title: t('task_center.group.bank_events'),
    });

    if (isErr(outcome)) {
      if (hasTag(outcome.error, 'BackendCancelled') && await pendingChallenge(bank)) {
        notifyAuthenticationRequired(bank);
      }
      else if (isCancellation(outcome.error)) {
        markLocationCancelled({ location, name });
      }
      else if (isActionable(outcome.error)) {
        logger.error(outcome.error);
        notifyError(
          t('actions.bank_events.error.title'),
          t('actions.bank_events.error.description', { error: outcome.error.message, location: bankName, name }),
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
