import { type MaybeRef } from '@vueuse/core';
import omit from 'lodash/omit';
import { type Collection } from '@/types/collection';
import {
  type HistoryEventEntry,
  type HistoryEventEntryWithMeta,
  type HistoryEventRequestPayload,
  type HistoryEventsCollectionResponse
} from '@/types/history/events';
import { defaultCollectionState } from '@/utils/collection';

export const useHistoryEvents = () => {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const { fetchHistoryEvents: fetchHistoryEventsCaller } =
    useHistoryEventsApi();

  const { fetchEnsNames } = useAddressesNamesStore();
  const fetchHistoryEvents = async (
    payload: MaybeRef<HistoryEventRequestPayload>
  ): Promise<Collection<HistoryEventEntry>> => {
    try {
      const result = await fetchHistoryEventsCaller(
        omit(get(payload), 'accounts')
      );

      const { data, ...other } = mapCollectionResponse<
        HistoryEventEntryWithMeta,
        HistoryEventsCollectionResponse
      >(result);

      const notesList: string[] = [];

      const mappedData = data.map((event: HistoryEventEntryWithMeta) => {
        const { entry, ...entriesMeta } = event;

        if (entry.notes) {
          notesList.push(entry.notes);
        }

        return {
          ...entry,
          ...entriesMeta
        };
      });

      if (!get(payload).groupByEventIds) {
        startPromise(fetchEnsNames(getEthAddressesFromText(notesList)));
      }

      return {
        ...other,
        data: mappedData
      };
    } catch (e: any) {
      logger.error(e);
      notify({
        title: t('actions.history_events.error.title').toString(),
        message: t('actions.history_events.error.description', {
          error: e
        }).toString(),
        display: true
      });
      return defaultCollectionState();
    }
  };

  return {
    fetchHistoryEvents
  };
};
