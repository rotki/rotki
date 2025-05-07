import type { ActionDataEntry } from '@/types/action';
import type { MaybeRef } from '@vueuse/core';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useScramble } from '@/composables/scramble';
import { useNotificationsStore } from '@/store/notifications';
import { isValidEthAddress, toHumanReadable } from '@rotki/common';
import { startPromise } from '@shared/utils';

export const useHistoryEventCounterpartyMappings = createSharedComposable(() => {
  const { getHistoryEventCounterpartiesData } = useHistoryEventsApi();

  const dataEntries = ref<ActionDataEntry[]>([]);

  const { scrambleAddress, scrambleData } = useScramble();
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

  const getEventCounterpartyData = (
    event: MaybeRef<{ counterparty: string | null; address?: string | null }>,
  ): ComputedRef<ActionDataEntry | null> => computed(() => {
    const { address, counterparty } = get(event);
    const excludedCounterparty = ['gas'];

    if (counterparty && excludedCounterparty.includes(counterparty))
      return null;

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
        icon: 'lu-circle-help',
        identifier: '',
        label: counterparty,
      };
    }

    const usedLabel = counterparty || address;

    if (!usedLabel)
      return null;

    const counterpartyAddress = get(scrambleData)
      ? scrambleAddress(usedLabel)
      : usedLabel;

    return {
      identifier: '',
      label: counterpartyAddress || '',
    };
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
      icon: 'lu-circle-help',
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
    getCounterpartyData,
    getEventCounterpartyData,
  };
});
