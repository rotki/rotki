import type { MaybeRef } from '@vueuse/core';
import type { ActionDataEntry } from '@/types/action';
import { isValidEthAddress, toHumanReadable } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useNotificationsStore } from '@/store/notifications';
import { getPublicProtocolImagePath } from '@/utils/file';

interface Counterparty {
  image: string;
  label: string;
}

export const useHistoryEventCounterpartyMappings = createSharedComposable(() => {
  const { getHistoryEventCounterpartiesData } = useHistoryEventsApi();

  const dataEntries = ref<ActionDataEntry[]>([]);

  const { notify } = useNotificationsStore();
  const { t } = useI18n({ useScope: 'global' });

  const fetchCounterparties = async (): Promise<void> => {
    try {
      set(dataEntries, await getHistoryEventCounterpartiesData());
    }
    catch (error: any) {
      notify({
        action: [
          {
            action: async (): Promise<void> => fetchCounterparties(),
            icon: 'lu-refresh-ccw',
            label: t('actions.fetch_counterparties.actions.fetch_again'),
          },
        ],
        display: true,
        message: t('actions.fetch_counterparties.error.description', {
          message: error.message,
        }),
        title: t('actions.fetch_counterparties.error.title'),
      });
    }
  };

  function getBaseCounterpartyData(counterparty: string, isDark?: boolean): Counterparty | undefined {
    const excludedCounterparty = ['gas'];
    if (excludedCounterparty.includes(counterparty))
      return undefined;

    if (counterparty && !isValidEthAddress(counterparty)) {
      const data = get(dataEntries).find(({ identifier, matcher }: ActionDataEntry) => matcher
        ? matcher(counterparty)
        : identifier.toLowerCase() === counterparty.toLowerCase());

      if (data) {
        const imageFile = data.darkmodeImage && isDark ? data.darkmodeImage : data.image;
        if (imageFile) {
          return {
            image: getPublicProtocolImagePath(imageFile),
            label: data.label || toHumanReadable(counterparty, 'capitalize'),
          };
        }
      }
    }
    return undefined;
  }

  const getEventCounterpartyData = (
    counterparty: MaybeRef<string | undefined>,
  ): ComputedRef<ActionDataEntry | undefined> => computed(() => {
    const counterpartyVal = get(counterparty);
    const excludedCounterparty = ['gas'];

    if (counterpartyVal && excludedCounterparty.includes(counterpartyVal))
      return undefined;

    if (counterpartyVal && !isValidEthAddress(counterpartyVal)) {
      const data = get(dataEntries).find(({ identifier, matcher }: ActionDataEntry) => {
        if (matcher)
          return matcher(counterpartyVal);

        return identifier.toLowerCase() === counterpartyVal.toLowerCase();
      });

      if (data) {
        return {
          ...data,
          label: data.label || toHumanReadable(counterpartyVal, 'capitalize'),
        };
      }

      return {
        color: 'error',
        icon: 'lu-circle-question-mark',
        identifier: '',
        label: counterpartyVal,
      };
    }

    return undefined;
  });

  const counterparties = useArrayMap(
    dataEntries,
    ({ identifier }) => identifier,
  );

  const getCounterpartyData = (counterparty: MaybeRef<string>): ComputedRef<ActionDataEntry> => computed(() => {
    const counterpartyVal = get(counterparty);
    const data = get(dataEntries).find(item => item.identifier === counterpartyVal);

    if (data)
      return data;

    return {
      color: 'error',
      icon: 'lu-circle-question-mark',
      identifier: counterpartyVal,
      label: counterpartyVal,
    };
  });

  onBeforeMount(() => {
    startPromise(fetchCounterparties());
  });

  return {
    counterparties,
    fetchCounterparties,
    getBaseCounterpartyData,
    getCounterpartyData,
    getEventCounterpartyData,
  };
});
