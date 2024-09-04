import type { ActionDataEntry } from '@/types/action';
import type { MaybeRef } from '@vueuse/core';

export const useHistoryEventCounterpartyMappings = createSharedComposable(() => {
  const { getHistoryEventCounterpartiesData } = useHistoryEventsApi();

  const dataEntries = ref<ActionDataEntry[]>([]);

  const { scrambleData, scrambleAddress } = useScramble();
  const { notify } = useNotificationsStore();
  const { t } = useI18n();

  const fetchCounterparties = async (): Promise<void> => {
    try {
      set(dataEntries, await getHistoryEventCounterpartiesData());
    }
    catch (error: any) {
      notify({
        display: true,
        title: t('actions.fetch_counterparties.error.title'),
        message: t('actions.fetch_counterparties.error.description', {
          message: error.message,
        }),
        action: [
          {
            label: t('actions.fetch_counterparties.actions.fetch_again'),
            action: async (): Promise<void> => await fetchCounterparties(),
            icon: 'refresh-line',
          },
        ],
      });
    }
  };

  const getEventCounterpartyData = (
    event: MaybeRef<{ counterparty: string | null; address?: string | null }>,
  ): ComputedRef<ActionDataEntry | null> => computed(() => {
    const { counterparty, address } = get(event);
    const excludedCounterparty = ['gas'];

    if (counterparty && excludedCounterparty.includes(counterparty))
      return null;

    if (counterparty && !isValidEthAddress(counterparty)) {
      const data = get(dataEntries).find(({ matcher, identifier }: ActionDataEntry) => {
        if (matcher)
          return matcher(counterparty);

        return identifier.toLowerCase() === counterparty.toLowerCase();
      });

      if (data) {
        return {
          ...data,
          label: counterparty.toUpperCase(),
        };
      }

      return {
        identifier: '',
        label: counterparty,
        icon: 'question-line',
        color: 'error',
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
      identifier: counterpartyVal,
      label: counterpartyVal,
      icon: 'question-line',
      color: 'error',
    };
  });

  onBeforeMount(() => {
    startPromise(fetchCounterparties());
  });

  return {
    getEventCounterpartyData,
    getCounterpartyData,
    fetchCounterparties,
    counterparties,
  };
});
