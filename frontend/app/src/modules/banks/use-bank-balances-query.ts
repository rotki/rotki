import type { ConnectionRef } from '@/modules/core/common/connection';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { map as mapResult, type Result } from 'plainfp/result';
import { useI18n } from 'vue-i18n';
import { msg } from '@/message-key';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { mergeConnectionBalances } from '@/modules/banks/bank-balances';
import { bankBalancesActivity, bankConnectionBalancesActivity } from '@/modules/banks/banks.activity';
import { BankBalancesResponse } from '@/modules/banks/types';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBanksApi } from '@/modules/banks/use-banks-api';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseBankBalancesQueryReturn {
  /**
   * Queries every bank, or only the given connection, as a task center activity.
   *
   * @remarks
   * With no connections the bank balances are cleared and nothing is submitted. Each connection in
   * the result replaces its own entry; the others keep their last known balances.
   *
   * @returns whether a query was submitted, false when there was no connection to query
   */
  queryBankBalances: (ignoreCache: boolean, connection?: ConnectionRef) => Promise<boolean>;
}

/**
 * Queries the bank balances as a task center activity and merges them into the balances store.
 */
export function useBankBalancesQuery(): UseBankBalancesQueryReturn {
  const { t } = useI18n({ useScope: 'global' });
  const api = useBanksApi();
  const store = useBankConnectionsStore();
  const { bankBalances } = storeToRefs(useBalancesStore());
  const { submitTask } = useNativeTask();

  const queryBankBalances = async (ignoreCache: boolean, connection?: ConnectionRef): Promise<boolean> => {
    if (get(store.connections).length === 0) {
      set(bankBalances, []);
      return false;
    }

    const activity = connection
      ? { id: bankConnectionBalancesActivity.id(connection), kind: bankConnectionBalancesActivity.kind, lane: bankConnectionBalancesActivity.laneOf?.(connection) }
      : { id: bankBalancesActivity.id(), kind: bankBalancesActivity.kind, lane: bankBalancesActivity.laneOf?.() };

    await submitTask({
      ...activity,
      rerunnable: true,
      run: async ({ rerun, runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<BankBalancesResponse>(async () => api.queryBankBalances(ignoreCache || rerun, connection)),
        (result) => {
          const fresh = BankBalancesResponse.parse(result).connections;
          set(bankBalances, mergeConnectionBalances(get(bankBalances), fresh));
        },
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.bank_balances.query')),
      title: t('task_center.group.bank_balances'),
    });
    return true;
  };

  return { queryBankBalances };
}
