import type { ActionStatus } from '@/types/action';
import type { Collection } from '@/types/collection';
import type { AddressBookSimplePayload } from '@/types/eth-names';
import type {
  AddHistoryEventPayload,
  HistoryEventEntry,
  HistoryEventEntryWithMeta,
  HistoryEventRequestPayload,
  HistoryEventsCollectionResponse,
  ModifyHistoryEventPayload,
} from '@/types/history/events';
import type { MaybeRef } from '@vueuse/core';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useSupportedChains } from '@/composables/info/chains';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useNotificationsStore } from '@/store/notifications';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { defaultCollectionState, mapCollectionResponse } from '@/utils/collection';
import { getEthAddressesFromText } from '@/utils/history';
import { logger } from '@/utils/logging';
import { startPromise } from '@shared/utils';
import { omit } from 'es-toolkit';

interface UseHistoryEventsReturn {
  fetchHistoryEvents: (payload: MaybeRef<HistoryEventRequestPayload>) => Promise<Collection<HistoryEventEntry>>;
  addHistoryEvent: (event: AddHistoryEventPayload) => Promise<ActionStatus<ValidationErrors | string>>;
  editHistoryEvent: (event: ModifyHistoryEventPayload) => Promise<ActionStatus<ValidationErrors | string>>;
  deleteHistoryEvent: (eventIds: number[], forceDelete?: boolean) => Promise<ActionStatus>;
  getEarliestEventTimestamp: () => Promise<number | undefined>;
}

export function useHistoryEvents(): UseHistoryEventsReturn {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const {
    addHistoryEvent: addHistoryEventCaller,
    deleteHistoryEvent: deleteHistoryEventCaller,
    editHistoryEvent: editHistoryEventCaller,
    fetchHistoryEvents: fetchHistoryEventsCaller,
  } = useHistoryEventsApi();

  const { fetchEnsNames } = useAddressesNamesStore();

  const { getChain } = useSupportedChains();

  const fetchHistoryEvents = async (
    payload: MaybeRef<HistoryEventRequestPayload & { accounts?: [] }>,
  ): Promise<Collection<HistoryEventEntry>> => {
    try {
      const formattedPayload = omit(get(payload), ['accounts']);
      const result = await fetchHistoryEventsCaller(formattedPayload);

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
        display: true,
        message: t('actions.history_events.error.description', {
          error,
        }).toString(),
        title: t('actions.history_events.error.title'),
      });
      return defaultCollectionState();
    }
  };

  const addHistoryEvent = async (event: AddHistoryEventPayload): Promise<ActionStatus<ValidationErrors | string>> => {
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

    return { message, success };
  };

  const editHistoryEvent = async (event: ModifyHistoryEventPayload): Promise<ActionStatus<ValidationErrors | string>> => {
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

    return { message, success };
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

    return { message, success };
  };

  const getEarliestEventTimestamp = async (): Promise<number | undefined> => {
    const response = await fetchHistoryEvents({
      ascending: [true],
      groupByEventIds: true,
      limit: 1,
      offset: 0,
      orderByAttributes: ['timestamp'],
    });

    if (response.data.length === 1) {
      return Math.floor(response.data[0].timestamp / 1000);
    }

    return undefined;
  };

  return {
    addHistoryEvent,
    deleteHistoryEvent,
    editHistoryEvent,
    fetchHistoryEvents,
    getEarliestEventTimestamp,
  };
}
