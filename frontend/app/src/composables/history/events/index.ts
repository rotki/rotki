import type { MaybeRef } from '@vueuse/core';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { ActionStatus } from '@/types/action';
import type { Collection } from '@/types/collection';
import type { AddressBookSimplePayload } from '@/types/eth-names';
import type {
  AddHistoryEventPayload,
  HistoryEventCollectionRow,
  HistoryEventRow,
  HistoryEventsCollectionResponse,
  ModifyHistoryEventPayload,
} from '@/types/history/events/schemas';
import { startPromise } from '@shared/utils';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useSupportedChains } from '@/composables/info/chains';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useNotificationsStore } from '@/store/notifications';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { defaultCollectionState, mapCollectionResponse } from '@/utils/collection';
import { millisecondsToSeconds } from '@/utils/date';
import { getEthAddressesFromText } from '@/utils/history';
import { logger } from '@/utils/logging';

interface UseHistoryEventsReturn {
  fetchHistoryEvents: (payload: MaybeRef<HistoryEventRequestPayload>) => Promise<Collection<HistoryEventRow>>;
  addHistoryEvent: (event: AddHistoryEventPayload) => Promise<ActionStatus<ValidationErrors | string>>;
  editHistoryEvent: (event: ModifyHistoryEventPayload) => Promise<ActionStatus<ValidationErrors | string>>;
  deleteHistoryEvent: (eventIds: number[], forceDelete?: boolean) => Promise<ActionStatus>;
  getEarliestEventTimestamp: () => Promise<number | undefined>;
}

export function useHistoryEvents(): UseHistoryEventsReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationsStore();

  const {
    addHistoryEvent: addHistoryEventCaller,
    deleteHistoryEvent: deleteHistoryEventCaller,
    editHistoryEvent: editHistoryEventCaller,
    fetchHistoryEvents: fetchHistoryEventsCaller,
  } = useHistoryEventsApi();

  const { fetchEnsNames } = useAddressesNamesStore();

  const { getChain } = useSupportedChains();

  function extractAddresses(
    notes: string | undefined,
    addressesNamesPayload: AddressBookSimplePayload[],
    location: string,
  ): void {
    if (!notes) {
      return;
    }
    addressesNamesPayload.push(
      ...getEthAddressesFromText(notes).map(address => ({
        address,
        blockchain: getChain(location),
      })),
    );
  }

  function populateAddressBook(collection: Collection<HistoryEventCollectionRow>): void {
    const addressesNamesPayload: AddressBookSimplePayload[] = [];

    for (const row of collection.data) {
      const events = Array.isArray(row) ? row : [row];
      for (const event of events) {
        const { autoNotes, location, userNotes } = event.entry;
        extractAddresses(userNotes, addressesNamesPayload, location);
        extractAddresses(autoNotes, addressesNamesPayload, location);
      }
    }

    if (addressesNamesPayload.length > 0)
      startPromise(fetchEnsNames(addressesNamesPayload));
  }

  const fetchHistoryEvents = async (
    payload: MaybeRef<HistoryEventRequestPayload>,
  ): Promise<Collection<HistoryEventRow>> => {
    try {
      const requestData = get(payload);
      const collection = mapCollectionResponse<
        HistoryEventCollectionRow,
        HistoryEventsCollectionResponse
      >(await fetchHistoryEventsCaller(requestData));

      if (!requestData.groupByEventIds) {
        populateAddressBook(collection);
      }

      const { data, ...others } = collection;

      const flatData: HistoryEventRow[] = [];

      for (const row of data) {
        if (!Array.isArray(row)) {
          const { entry, ...meta } = row;
          flatData.push({ ...entry, ...meta });
        }
        else {
          const events = row.map((event) => {
            const { entry, ...meta } = event;
            return ({ ...entry, ...meta });
          });
          flatData.push(events);
        }
      }

      return { data: flatData, ...others };
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
      const firstRow = response.data[0];
      const timestamp = Array.isArray(firstRow) ? firstRow[0].timestamp : firstRow.timestamp;
      return millisecondsToSeconds(timestamp);
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
