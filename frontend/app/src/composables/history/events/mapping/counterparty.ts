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
    event: MaybeRef<{ counterparty: string | null }>,
  ): ComputedRef<ActionDataEntry | undefined> => computed(() => {
    const { counterparty } = get(event);
    const excludedCounterparty = ['gas'];

    if (counterparty && excludedCounterparty.includes(counterparty))
      return undefined;

    if (counterparty && !isValidEthAddress(counterparty)) {
      const data = get(dataEntries).find(({ identifier, matcher }: ActionDataEntry) => {
        if (matcher)
          return matcher(counterparty);

        return identifier.toLowerCase() === counterparty.toLowerCase();
      });

      if (data) {
        return {
          ...data,
          label: data.label || toHumanReadable(counterparty, 'capitalize'),
        };
      }

      return {
        color: 'error',
        icon: 'lu-circle-question-mark',
        identifier: '',
        label: counterparty,
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
