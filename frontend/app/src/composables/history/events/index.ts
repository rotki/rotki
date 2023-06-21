import { type MaybeRef } from '@vueuse/core';
import omit from 'lodash/omit';
import { type Collection } from '@/types/collection';
import {
  type HistoryEventEntry,
  type HistoryEventEntryWithMeta,
  type HistoryEventRequestPayload,
  type HistoryEventsCollectionResponse
} from '@/types/history/events';
import { type AddressBookSimplePayload } from '@/types/eth-names';

export const useHistoryEvents = () => {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const { fetchHistoryEvents: fetchHistoryEventsCaller } =
    useHistoryEventsApi();

  const { fetchEnsNames } = useAddressesNamesStore();

  const { getChain } = useSupportedChains();

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

      const addressesNamesPayload: AddressBookSimplePayload[] = [];
      const mappedData = data.map((event: HistoryEventEntryWithMeta) => {
        const { entry, ...entriesMeta } = event;

        if (!get(payload).groupByEventIds && entry.notes) {
          const addresses = getEthAddressesFromText(entry.notes);
          addressesNamesPayload.push(
            ...addresses.map(address => ({
              address,
              blockchain: getChain(entry.location)
            }))
          );
        }

        return {
          ...entry,
          ...entriesMeta
        };
      });

      if (addressesNamesPayload.length > 0) {
        startPromise(fetchEnsNames(addressesNamesPayload));
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
