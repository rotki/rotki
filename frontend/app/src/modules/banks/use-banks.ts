import type { ResultAsync } from 'plainfp/result-async';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { startPromise } from '@shared/utils';
import { isOk, map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { isSameConnection, mergeConnectionBalances } from '@/modules/banks/bank-balances';
import { bankBalancesActivity, bankConnectionBalancesActivity } from '@/modules/banks/banks.activity';
import {
  BankBalancesResponse,
  type BankConnectionIdentity,
  type BankFormData,
  type BankSetupError,
  type BankSetupResult,
  type BankSyncPayload,
  isBankSetupComplete,
} from '@/modules/banks/types';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBanksApi } from '@/modules/banks/use-banks-api';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useBankEventsRefresh } from '@/modules/history/events/tx/use-bank-events-refresh';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseBanksReturn {
  /** Loads the supported banks; a failure is kept in the store for the bank pages to show, not notified. */
  refreshSupportedBanks: () => Promise<void>;
  /**
   * Loads the connections; a failure is kept in the store for the bank pages to show, not notified.
   *
   * @remarks
   * Background work (a balance refresh, the load at login) calls this too, so the failure waits for
   * a bank page to be opened instead of interrupting whatever the user is doing.
   */
  refreshBankConnections: () => Promise<void>;
  /** Adds or edits a connection, refreshing the connections and balances once the backend accepts it. */
  setupBank: (form: BankFormData) => ResultAsync<BankSetupResult, BankSetupError>;
  /**
   * Answers a connection's pending challenge.
   *
   * @remarks
   * Every outcome re-reads the connections: the backend records a further challenge, and drops a
   * TAN the bank rejected or let expire, which the connection then reports as expired.
   */
  answerBankAuthentication: (connection: BankConnectionIdentity, response?: string) => ResultAsync<BankSetupResult, BankSetupError>;
  removeBank: (connection: BankConnectionIdentity) => Promise<boolean>;
  /**
   * Drops the challenge a connection waits on and syncs it again, so the bank sends a fresh one.
   *
   * @remarks
   * Only the bank knows when a challenge lapsed, so a challenge nobody answers would otherwise be
   * raised again by every query. The connections are re-read before the sync, so the dropped
   * challenge is not offered while the sync waits for its turn.
   */
  startOverAuthentication: (connection: BankConnectionIdentity) => Promise<void>;
  /**
   * Drops a setup left waiting on a TAN when its dialog closes, with the bank session it saved.
   *
   * @remarks
   * A failure is only logged: the backend also discards it when the same name is added again.
   */
  cancelBankSetup: (connection: BankConnectionIdentity) => Promise<void>;
  /** Pulls new transactions of one connection, of one bank, or of every connection. */
  syncBanks: (payload?: BankSyncPayload) => Promise<boolean>;
  /**
   * Queries every bank, or only the given connection, into the bank balances.
   *
   * @remarks
   * Each connection in the result replaces its own entry. The others keep their last known
   * balances, so a bank waiting on a TAN still counts what it last reported.
   */
  fetchBankBalances: (ignoreCache?: boolean, connection?: BankConnectionIdentity) => Promise<void>;
}

/**
 * The async side of the bank connections: everything here talks to the backend and writes the
 * result into {@link useBankConnectionsStore} or the balances store.
 */
export function useBanks(): UseBanksReturn {
  const { t } = useI18n({ useScope: 'global' });
  const api = useBanksApi();
  const store = useBankConnectionsStore();
  const { bankBalances } = storeToRefs(useBalancesStore());
  const { notifyError } = useNotifications();
  const { submitTask } = useNativeTask();
  const { queryAllBankEvents } = useBankEventsRefresh();

  const refreshSupportedBanks = async (): Promise<void> => {
    try {
      store.setManifests(await api.getSupportedBanks());
    }
    catch (error: unknown) {
      if (!isRequestCancellation(error))
        store.setManifestsError(error);
    }
  };

  const refreshBankConnections = async (): Promise<void> => {
    try {
      store.setConnections(await api.getBanks());
    }
    catch (error: unknown) {
      if (!isRequestCancellation(error))
        store.setConnectionsError(error);
    }
  };

  const fetchBankBalances = async (ignoreCache = false, connection?: BankConnectionIdentity): Promise<void> => {
    if (get(store.connections).length === 0) {
      set(bankBalances, []);
      return;
    }

    const activity = connection
      ? { id: bankConnectionBalancesActivity.id(connection), kind: bankConnectionBalancesActivity.kind, lane: bankConnectionBalancesActivity.laneOf?.(connection) }
      : { id: bankBalancesActivity.id(), kind: bankBalancesActivity.kind, lane: bankBalancesActivity.laneOf?.() };

    await submitTask({
      ...activity,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<BankBalancesResponse>(async () => api.queryBankBalances(ignoreCache, connection)),
        (result) => {
          const fresh = BankBalancesResponse.parse(result).connections;
          set(bankBalances, mergeConnectionBalances(get(bankBalances), fresh));
        },
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.bank_balances.query')),
      title: t('task_center.group.bank_balances'),
    });
    await refreshBankConnections();
  };

  const resolveSyncTargets = ({ connector, name }: BankSyncPayload): BankConnectionIdentity[] =>
    get(store.connections)
      .filter(connection => connector === undefined || connection.connector === connector)
      .filter(connection => name === undefined || connection.name === name)
      .map(connection => ({ connector: connection.connector, name: connection.name }));

  /**
   * The bank events activity re-reads the connections after it ran. With nothing to sync it never
   * runs, so the list is re-read here: the store may not hold a connection added a moment ago.
   */
  const syncBanks = async (payload: BankSyncPayload = {}): Promise<boolean> => {
    const targets = resolveSyncTargets(payload);
    if (targets.length === 0) {
      await refreshBankConnections();
      return false;
    }
    const outcomes = await queryAllBankEvents(targets);
    return outcomes.every(outcome => isOk(outcome));
  };

  /** A blank credential in an edit means "keep the stored one", which the backend only accepts as an absent slot. */
  const filledCredentials = (credentials: Record<string, string>): Record<string, string> =>
    Object.fromEntries(Object.entries(credentials).filter(([, value]) => value.trim() !== ''));

  const setupBank = async (form: BankFormData): ResultAsync<BankSetupResult, BankSetupError> => {
    const { connector, credentials, mode, name, newName } = form;
    const outcome = mode === 'edit'
      ? mapResult(
          await api.editBank({ connector, credentials: filledCredentials(credentials), name, newName: newName === name ? undefined : newName }),
          (): true => true,
        )
      : await api.addBank({ connector, credentials, name });
    if (outcome.ok && isBankSetupComplete(outcome.value)) {
      await refreshBankConnections();
      startPromise(fetchBankBalances());
      if (mode === 'add') {
        startPromise(syncBanks({ connector, name }));
      }
    }
    return outcome;
  };

  const answerBankAuthentication = async (
    { connector, name }: BankConnectionIdentity,
    response?: string,
  ): ResultAsync<BankSetupResult, BankSetupError> => {
    const connection = { connector, name };
    const outcome = await api.answerAuthentication({ ...connection, response });
    await refreshBankConnections();
    if (outcome.ok && isBankSetupComplete(outcome.value)) {
      startPromise(fetchBankBalances());
      if (outcome.value !== true) {
        startPromise(syncBanks(connection));
      }
    }
    return outcome;
  };

  const removeBank = async (connection: BankConnectionIdentity): Promise<boolean> => {
    try {
      const success = await api.removeBank(connection);
      if (success) {
        set(bankBalances, get(bankBalances).filter(entry => !isSameConnection(entry, connection)));
        await refreshBankConnections();
        startPromise(fetchBankBalances());
      }
      return success;
    }
    catch (error: unknown) {
      notifyError(
        t('bank_settings.errors.remove_title'),
        t('bank_settings.errors.remove_message', { error: getErrorMessage(error), name: connection.name }),
      );
      return false;
    }
  };

  const startOverAuthentication = async (connection: BankConnectionIdentity): Promise<void> => {
    try {
      await api.cancelAuthentication(connection);
    }
    catch (error: unknown) {
      notifyError(
        t('bank_settings.errors.start_over_title'),
        t('bank_settings.errors.start_over_message', { error: getErrorMessage(error), name: connection.name }),
      );
      await refreshBankConnections();
      return;
    }
    await refreshBankConnections();
    await syncBanks(connection);
  };

  const cancelBankSetup = async (connection: BankConnectionIdentity): Promise<void> => {
    try {
      await api.cancelAuthentication(connection);
    }
    catch (error: unknown) {
      logger.warn(`Could not drop the ${connection.name} bank setup: ${getErrorMessage(error)}`);
    }
  };

  return {
    answerBankAuthentication,
    cancelBankSetup,
    fetchBankBalances,
    refreshBankConnections,
    refreshSupportedBanks,
    removeBank,
    setupBank,
    startOverAuthentication,
    syncBanks,
  };
}
