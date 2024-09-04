import { omit } from 'lodash-es';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import type { MaybeRef } from '@vueuse/core';
import type { Collection } from '@/types/collection';
import type {
  EditHistoryEventPayload,
  HistoryEventEntry,
  HistoryEventEntryWithMeta,
  HistoryEventRequestPayload,
  HistoryEventsCollectionResponse,
  NewHistoryEventPayload,
} from '@/types/history/events';
import type { AddressBookSimplePayload } from '@/types/eth-names';
import type { ActionStatus } from '@/types/action';

interface UseHistoryEventsReturn {
  fetchHistoryEvents: (payload: MaybeRef<HistoryEventRequestPayload>) => Promise<Collection<HistoryEventEntry>>;
  addHistoryEvent: (event: NewHistoryEventPayload) => Promise<ActionStatus<ValidationErrors | string>>;
  editHistoryEvent: (event: EditHistoryEventPayload) => Promise<ActionStatus<ValidationErrors | string>>;
  deleteHistoryEvent: (eventIds: number[], forceDelete?: boolean) => Promise<ActionStatus>;
}

export function useHistoryEvents(): UseHistoryEventsReturn {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const {
    fetchHistoryEvents: fetchHistoryEventsCaller,
    deleteHistoryEvent: deleteHistoryEventCaller,
    addHistoryEvent: addHistoryEventCaller,
    editHistoryEvent: editHistoryEventCaller,
  } = useHistoryEventsApi();

  const { fetchEnsNames } = useAddressesNamesStore();

  const { getChain } = useSupportedChains();

  const fetchHistoryEvents = async (
    payload: MaybeRef<HistoryEventRequestPayload>,
  ): Promise<Collection<HistoryEventEntry>> => {
    try {
      const result = await fetchHistoryEventsCaller(omit(get(payload), 'accounts'));

      const { data, ...other } = mapCollectionResponse<HistoryEventEntryWithMeta, HistoryEventsCollectionResponse>(
        result,
      );

      const addressesNamesPayload: AddressBookSimplePayload[] = [];
      const mappedData = data.map((event: HistoryEventEntryWithMeta) => {
        const { entry, ...entriesMeta } = event;

        if (!get(payload).groupByEventIds && entry.notes) {
          const addresses = getEthAddressesFromText(entry.notes);
          addressesNamesPayload.push(
            ...addresses.map(address => ({
              address,
              blockchain: getChain(entry.location),
            })),
          );
        }

        return {
          ...entry,
          ...entriesMeta,
        };
      });

      if (addressesNamesPayload.length > 0)
        startPromise(fetchEnsNames(addressesNamesPayload));

      return {
        ...other,
        data: mappedData,
      };
    }
    catch (error: any) {
      logger.error(error);
      notify({
        title: t('actions.history_events.error.title').toString(),
        message: t('actions.history_events.error.description', {
          error,
        }).toString(),
        display: true,
      });
      return defaultCollectionState();
    }
  };

  const addHistoryEvent = async (event: NewHistoryEventPayload): Promise<ActionStatus<ValidationErrors | string>> => {
    let success = false;
    let message: ValidationErrors | string = '';
    try {
      await addHistoryEventCaller(event);
      success = true;
    }
    catch (error: any) {
      message = error.message;
      if (error instanceof ApiValidationError)
        message = error.getValidationErrors(event);
    }

    return { success, message };
  };

  const editHistoryEvent = async (event: EditHistoryEventPayload): Promise<ActionStatus<ValidationErrors | string>> => {
    let success = false;
    let message: ValidationErrors | string = '';
    try {
      await editHistoryEventCaller(event);
      success = true;
    }
    catch (error: any) {
      message = error.message;
      if (error instanceof ApiValidationError)
        message = error.getValidationErrors(event);
    }

    return { success, message };
  };

  const deleteHistoryEvent = async (eventIds: number[], forceDelete = false): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      success = await deleteHistoryEventCaller(eventIds, forceDelete);
    }
    catch (error: any) {
      message = error.message;
    }

    return { success, message };
  };

  return {
    fetchHistoryEvents,
    addHistoryEvent,
    editHistoryEvent,
    deleteHistoryEvent,
  };
}
