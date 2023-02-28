import { type MaybeRef } from '@vueuse/core';
import { type Collection, type CollectionResponse } from '@/types/collection';
import { type SupportedExchange } from '@/types/exchanges';
import {
  type LedgerAction,
  type LedgerActionEntry,
  type LedgerActionRequestPayload,
  type NewLedgerAction
} from '@/types/history/ledger-action/ledger-actions';
import { type EntryWithMeta } from '@/types/history/meta';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { mapCollectionResponse } from '@/utils/collection';
import { logger } from '@/utils/logging';
import { mapCollectionEntriesWithMeta } from '@/utils/history';
import { type ActionStatus } from '@/types/action';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';

export const useLedgerActionStore = defineStore(
  'history/ledger-actions',
  () => {
    const locationsStore = useAssociatedLocationsStore();
    const { connectedExchanges } = storeToRefs(locationsStore);
    const { fetchAssociatedLocations } = locationsStore;
    const { exchangeName } = useTradeLocations();
    const { awaitTask } = useTaskStore();
    const { tc } = useI18n();
    const { notify } = useNotificationsStore();

    const {
      getLedgerActions,
      getLedgerActionsTask,
      addLedgerAction: addLedgerActionCaller,
      editLedgerAction: editLedgerActionCaller,
      deleteLedgerAction: deleteLedgerActionCaller
    } = useLedgerActionsApi();

    const syncLedgerActions = async (
      location: SupportedExchange
    ): Promise<boolean> => {
      const taskType = TaskType.LEDGER_ACTIONS;

      const defaults: LedgerActionRequestPayload = {
        limit: 0,
        offset: 0,
        ascending: [false],
        orderByAttributes: ['timestamp'],
        onlyCache: false,
        location
      };

      const exchange = exchangeName(location);

      try {
        const { taskId } = await getLedgerActionsTask(defaults);
        const taskMeta = {
          title: tc('actions.ledger_actions.task.title'),
          description: tc('actions.ledger_actions.task.description', 0, {
            exchange
          }),
          location
        };

        await awaitTask<
          CollectionResponse<EntryWithMeta<LedgerAction>>,
          TaskMeta
        >(taskId, taskType, taskMeta, true);
        return true;
      } catch (e: any) {
        notify({
          title: tc('actions.ledger_actions.error.title', 0, {
            exchange
          }),
          message: tc('actions.ledger_actions.error.description', 0, {
            exchange,
            error: e
          }),
          display: true
        });
      }
      return false;
    };

    const refreshLedgerActions = async (
      userInitiated = false,
      location?: SupportedExchange
    ): Promise<void> => {
      const { setStatus, isFirstLoad, resetStatus, fetchDisabled } =
        useStatusUpdater(Section.LEDGER_ACTIONS);

      if (fetchDisabled(userInitiated)) {
        logger.info('skipping ledger action refresh');
        return;
      }

      await fetchAssociatedLocations();
      const locations = location
        ? [location]
        : get(connectedExchanges).map(x => x.location);

      try {
        setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING);
        await Promise.all(locations.map(syncLedgerActions));
        setStatus(Status.LOADED);
      } catch (e: any) {
        logger.error(e);
        resetStatus();
      }
    };

    const fetchLedgerActions = async (
      payload: MaybeRef<LedgerActionRequestPayload>
    ): Promise<Collection<LedgerActionEntry>> => {
      const result = await getLedgerActions({
        ...get(payload),
        onlyCache: true
      });
      return mapCollectionEntriesWithMeta<LedgerAction>(
        mapCollectionResponse(result)
      );
    };

    const addLedgerAction = async (
      ledgerAction: NewLedgerAction
    ): Promise<ActionStatus<ValidationErrors | string>> => {
      let success = false;
      let message: ValidationErrors | string = '';
      try {
        await addLedgerActionCaller(ledgerAction);
        success = true;
      } catch (e: any) {
        message = e.message;
        if (e instanceof ApiValidationError) {
          message = e.getValidationErrors(ledgerAction);
        }
      }

      await fetchAssociatedLocations();
      return { success, message };
    };

    const editLedgerAction = async (
      ledgerAction: LedgerActionEntry
    ): Promise<ActionStatus<ValidationErrors | string>> => {
      let success = false;
      let message: ValidationErrors | string = '';
      try {
        await editLedgerActionCaller(ledgerAction);
        success = true;
      } catch (e: any) {
        message = e.message;
        if (e instanceof ApiValidationError) {
          message = e.getValidationErrors(ledgerAction);
        }
      }

      await fetchAssociatedLocations();
      return { success, message };
    };

    const deleteLedgerAction = async (
      identifiers: number[]
    ): Promise<ActionStatus> => {
      let success = false;
      let message = '';
      try {
        success = await deleteLedgerActionCaller(identifiers);
      } catch (e: any) {
        message = e.message;
      }

      await fetchAssociatedLocations();
      return { success, message };
    };

    return {
      refreshLedgerActions,
      fetchLedgerActions,
      addLedgerAction,
      editLedgerAction,
      deleteLedgerAction
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useLedgerActionStore, import.meta.hot)
  );
}
