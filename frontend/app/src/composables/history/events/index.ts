import type { MaybeRef } from 'vue';
import type { AddressBookSimplePayload } from '@/modules/address-names/eth-names';
import type { ActionStatus } from '@/modules/common/action';
import type { Collection } from '@/modules/common/collection';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type {
  AddHistoryEventPayload,
  HistoryEventCollectionRow,
  HistoryEventRow,
  HistoryEventsCollectionResponse,
  ModifyHistoryEventPayload,
} from '@/modules/history/events/schemas';
import { startPromise } from '@shared/utils';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useSupportedChains } from '@/composables/info/chains';
import { useEnsOperations } from '@/modules/address-names/use-ens-operations';
import { RequestCancelledError } from '@/modules/api/request-queue/errors';
import { ApiValidationError, type ValidationErrors } from '@/modules/api/types/errors';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { useHistoryStore } from '@/store/history';
import { arrayify } from '@/utils/array';
import { defaultCollectionState, mapCollectionResponse } from '@/utils/collection';
import { millisecondsToSeconds } from '@/utils/date';
import { getErrorMessage } from '@/utils/error-handling';
import { getEthAddressesFromText } from '@/utils/history';
import { logger } from '@/utils/logging';

interface UseHistoryEventsReturn {
  fetchHistoryEvents: (payload: MaybeRef<HistoryEventRequestPayload>, options?: { tags?: string[] }) => Promise<Collection<HistoryEventRow>>;
  addHistoryEvent: (event: AddHistoryEventPayload) => Promise<ActionStatus<ValidationErrors | string>>;
  editHistoryEvent: (event: ModifyHistoryEventPayload) => Promise<ActionStatus<ValidationErrors | string>>;
  deleteHistoryEvent: (eventIds: number[], forceDelete?: boolean) => Promise<ActionStatus>;
  getEarliestEventTimestamp: () => Promise<number | undefined>;
}

export function useHistoryEvents(): UseHistoryEventsReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();

  const {
    addHistoryEvent: addHistoryEventCaller,
    deleteHistoryEvent: deleteHistoryEventCaller,
    editHistoryEvent: editHistoryEventCaller,
    fetchHistoryEvents: fetchHistoryEventsCaller,
  } = useHistoryEventsApi();

  const { signalEventsModified } = useHistoryStore();
  const { fetchEnsNames } = useEnsOperations();

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
      const events = arrayify(row);
      for (const { entry } of events) {
        extractAddresses(entry.userNotes, addressesNamesPayload, entry.location);
        extractAddresses(entry.autoNotes, addressesNamesPayload, entry.location);

        if ('address' in entry && entry.address) {
          extractAddresses(entry.address, addressesNamesPayload, entry.location);
        }
      }
    }

    if (addressesNamesPayload.length > 0)
      startPromise(fetchEnsNames(addressesNamesPayload));
  }

  const fetchHistoryEvents = async (
    payload: MaybeRef<HistoryEventRequestPayload>,
    options?: { tags?: string[] },
  ): Promise<Collection<HistoryEventRow>> => {
    try {
      const requestData = get(payload);
      const collection = mapCollectionResponse<
        HistoryEventCollectionRow,
        HistoryEventsCollectionResponse
      >(await fetchHistoryEventsCaller(requestData, options));

      if (!requestData.aggregateByGroupIds) {
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
    catch (error: unknown) {
      if (error instanceof RequestCancelledError)
        throw error;

      logger.error(error);
      notifyError(
        t('actions.history_events.error.title'),
        t('actions.history_events.error.description', { error }).toString(),
      );
      return defaultCollectionState();
    }
  };

  const addHistoryEvent = async (event: AddHistoryEventPayload): Promise<ActionStatus<ValidationErrors | string>> => {
    let success = false;
    let message: ValidationErrors | string = '';
    try {
      await addHistoryEventCaller(event);
      success = true;
      signalEventsModified();
    }
    catch (error: unknown) {
      message = getErrorMessage(error);
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
      signalEventsModified();
    }
    catch (error: unknown) {
      message = getErrorMessage(error);
      if (error instanceof ApiValidationError)
        message = error.getValidationErrors(event);
    }

    return { message, success };
  };

  const deleteHistoryEvent = async (eventIds: number[], forceDelete = false): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      success = await deleteHistoryEventCaller({ identifiers: eventIds.map(id => id.toString()) }, forceDelete);
      if (success)
        signalEventsModified();
    }
    catch (error: unknown) {
      message = getErrorMessage(error);
    }

    return { message, success };
  };

  const getEarliestEventTimestamp = async (): Promise<number | undefined> => {
    const response = await fetchHistoryEvents({
      aggregateByGroupIds: true,
      ascending: [true],
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
