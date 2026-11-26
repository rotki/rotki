import type { MaybeRef } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type { Collection } from '@/modules/core/common/collection';
import type { AddHistoryEventPayload, HistoryEventRequestPayload, ModifyHistoryEventPayload } from '@/modules/history/events/request-types';
import type { HistoryEventCollectionRow, HistoryEventRow, HistoryEventsCollectionResponse } from '@/modules/history/events/schemas';
import { get } from '@vueuse/shared';
import { err, fromPromise, map, ok, type ResultAsync } from 'plainfp/result-async';
import { useI18n } from 'vue-i18n';
import { fromRequest, isRequestFailure, type RequestError } from '@/modules/core/api/request-result';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';
import { millisecondsToSeconds } from '@/modules/core/common/data/date';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage } from '@/modules/core/notifications/use-notifications';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useHistoryEventsAddressBook } from '@/modules/history/events/use-history-events-address-book';
import { useHistoryStore } from '@/modules/history/use-history-store';

interface UseHistoryEventsReturn {
  fetchHistoryEvents: (payload: MaybeRef<HistoryEventRequestPayload>, options?: { tags?: string[] }) => ResultAsync<Collection<HistoryEventRow>, RequestError>;
  addHistoryEvent: (event: AddHistoryEventPayload) => Promise<ActionStatus<ValidationErrors | string>>;
  editHistoryEvent: (event: ModifyHistoryEventPayload) => Promise<ActionStatus<ValidationErrors | string>>;
  /** @returns `err` with the request's own error, or a worded refusal when the backend answers `false` */
  deleteHistoryEvent: (eventIds: number[], forceDelete?: boolean) => ResultAsync<void, unknown>;
  getEarliestEventTimestamp: () => Promise<number | undefined>;
}

export function useHistoryEvents(): UseHistoryEventsReturn {
  const { t } = useI18n({ useScope: 'global' });
  const {
    addHistoryEvent: addHistoryEventCaller,
    deleteHistoryEvent: deleteHistoryEventCaller,
    editHistoryEvent: editHistoryEventCaller,
    fetchHistoryEvents: fetchHistoryEventsCaller,
  } = useHistoryEventsApi();

  const { signalEventsModified } = useHistoryStore();
  const { populateAddressBook } = useHistoryEventsAddressBook();

  /** Flattens each row's `entry` into the row, keeping grouped rows as arrays. */
  function toEventRows(collection: Collection<HistoryEventCollectionRow>): Collection<HistoryEventRow> {
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

  const fetchHistoryEvents = async (
    payload: MaybeRef<HistoryEventRequestPayload>,
    options?: { tags?: string[] },
  ): ResultAsync<Collection<HistoryEventRow>, RequestError> => {
    const requestData = get(payload);

    const response = fromRequest(async () => mapCollectionResponse<
      HistoryEventCollectionRow,
      HistoryEventsCollectionResponse
    >(await fetchHistoryEventsCaller(requestData, options)));

    return map(response, (collection) => {
      if (!requestData.aggregateByGroupIds)
        populateAddressBook(collection);

      return toEventRows(collection);
    });
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

  const deleteHistoryEvent = async (eventIds: number[], forceDelete = false): ResultAsync<void, unknown> => {
    const answer = await fromPromise(
      deleteHistoryEventCaller({ identifiers: eventIds.map(id => id.toString()) }, forceDelete),
      (error: unknown) => error,
    );
    if (!answer.ok)
      return answer;
    if (!answer.value)
      return err(t('transactions.events.delete.error.message'));

    signalEventsModified();
    return ok(undefined);
  };

  const getEarliestEventTimestamp = async (): Promise<number | undefined> => {
    const response = await fetchHistoryEvents({
      aggregateByGroupIds: true,
      ascending: [true],
      limit: 1,
      offset: 0,
      orderByAttributes: ['timestamp'],
    });

    if (!response.ok) {
      if (isRequestFailure(response.error))
        logger.error(response.error.cause);
      return undefined;
    }

    if (response.value.data.length === 1) {
      const firstRow = response.value.data[0];
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
