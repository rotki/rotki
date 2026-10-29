import type { ResultAsync } from 'plainfp/result-async';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { startPromise } from '@shared/utils';
import { isOk, map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { bankBalancesActivity } from '@/modules/banks/banks.activity';
import {
  BankBalancesByLocation,
  type BankConnection,
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
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useBankEventsRefresh } from '@/modules/history/events/tx/use-bank-events-refresh';
import { useSetting } from '@/modules/settings/use-setting';
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
  answerBankAuthentication: (connection: { identifier: string }, response?: string) => ResultAsync<BankSetupResult, BankSetupError>;
  removeBank: (connection: { identifier: string }) => Promise<boolean>;
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
  cancelBankSetup: (setup: { identifier: string; name: string }) => Promise<void>;
  /** Pulls new transactions of one connection, of one bank, or of every connection. */
  syncBanks: (payload?: BankSyncPayload) => Promise<boolean>;
  /** Queries every connected bank's balances into the per-location balance map. */
  fetchBankBalances: (ignoreCache?: boolean) => Promise<void>;
}

/**
 * The async side of the bank connections: everything here talks to the backend and writes the
 * result into {@link useBankConnectionsStore} or the balances store.
 */
export function useBanks(): UseBanksReturn {
  const { t } = useI18n({ useScope: 'global' });
  const api = useBanksApi();
  const store = useBankConnectionsStore();
  const { exchangeBalances } = storeToRefs(useBalancesStore());
  const { balanceLocations, bankLocations } = storeToRefs(store);
  const { notifyError, notifyInfo } = useNotifications();
  const dateDisplayFormat = useSetting('dateDisplayFormat');
  const { submitTask } = useNativeTask();
  const { queryAllBankEvents } = useBankEventsRefresh();

  function notifyHistoryLimit(result: BankSetupResult): void {
    if (result === true || !('success' in result) || result.historyStartTs === null)
      return;
    notifyInfo(
      t('bank_settings.history_limit.title'),
      t('bank_settings.history_limit.message', {
        date: displayDateFormatter.format(
          new Date(result.historyStartTs * 1000),
          get(dateDisplayFormat),
        ),
      }),
    );
  }

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

  /**
   * The per-location map minus every bank, ready to receive a fresh bank result. The locations of
   * the previous result count as banks too, so the balances of a removed connection go with it.
   */
  const withoutBanks = (): Record<string, BankBalancesByLocation[string]> => {
    const banks = new Set<string>([...get(bankLocations), ...get(balanceLocations)]);
    return Object.fromEntries(Object.entries(get(exchangeBalances)).filter(([location]) => !banks.has(location)));
  };

  const fetchBankBalances = async (ignoreCache = false): Promise<void> => {
    if (get(store.connections).length === 0) {
      set(exchangeBalances, withoutBanks());
      store.setBalanceLocations([]);
      return;
    }

    await submitTask({
      id: bankBalancesActivity.id(),
      kind: bankBalancesActivity.kind,
      lane: bankBalancesActivity.laneOf?.(),
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<BankBalancesByLocation>(async () => api.queryBankBalances(ignoreCache)),
        (result) => {
          const balances = BankBalancesByLocation.parse(result);
          set(exchangeBalances, { ...withoutBanks(), ...balances });
          store.setBalanceLocations(Object.keys(balances));
        },
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.bank_balances.query')),
      title: t('task_center.group.bank_balances'),
    });
    await refreshBankConnections();
  };

  const resolveSyncTargets = ({ connector, identifier }: BankSyncPayload): BankConnection[] =>
    get(store.connections)
      .filter(connection => connector === undefined || connection.connector === connector)
      .filter(connection => identifier === undefined || connection.identifier === identifier);

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
    const { connector, credentials, identifier, location, mode, name, newName } = form;
    const outcome = mode === 'edit' && identifier !== undefined
      ? mapResult(
          await api.editBank({ credentials: filledCredentials(credentials), identifier, newName: newName === name ? undefined : newName }),
          (): true => true,
        )
      : await api.addBank({ connector, credentials, location: location === '' ? undefined : location, name });
    if (outcome.ok && isBankSetupComplete(outcome.value)) {
      await refreshBankConnections();
      startPromise(fetchBankBalances());
      if (outcome.value !== true) {
        notifyHistoryLimit(outcome.value);
        startPromise(syncBanks({ identifier: outcome.value.identifier }));
      }
    }
    return outcome;
  };

  const answerBankAuthentication = async (
    { identifier }: { identifier: string },
    response?: string,
  ): ResultAsync<BankSetupResult, BankSetupError> => {
    const outcome = await api.answerAuthentication({ identifier, response });
    await refreshBankConnections();
    if (outcome.ok && isBankSetupComplete(outcome.value)) {
      startPromise(fetchBankBalances());
      if (outcome.value !== true) {
        notifyHistoryLimit(outcome.value);
        startPromise(syncBanks({ identifier }));
      }
    }
    return outcome;
  };

  const removeBank = async (connection: { identifier: string }): Promise<boolean> => {
    try {
      const success = await api.removeBank(connection);
      if (success) {
        await refreshBankConnections();
        startPromise(fetchBankBalances());
      }
      return success;
    }
    catch (error: unknown) {
      notifyError(
        t('bank_settings.errors.remove_title'),
        t('bank_settings.errors.remove_message', { error: getErrorMessage(error), name: store.connectionName(connection.identifier) }),
      );
      return false;
    }
  };

  const startOverAuthentication = async (connection: BankConnectionIdentity): Promise<void> => {
    try {
      await api.cancelAuthentication({ identifier: connection.identifier });
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
    await syncBanks({ identifier: connection.identifier });
  };

  const cancelBankSetup = async (setup: { identifier: string; name: string }): Promise<void> => {
    try {
      await api.cancelAuthentication({ identifier: setup.identifier });
    }
    catch (error: unknown) {
      logger.warn(`Could not drop the ${setup.name} bank setup: ${getErrorMessage(error)}`);
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
