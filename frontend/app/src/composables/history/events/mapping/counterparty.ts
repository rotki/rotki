import type { ActionDataEntry } from '@/types/action';
import type { MaybeRef } from '@vueuse/core';

export const useHistoryEventCounterpartyMappings = createSharedComposable(() => {
  const {
    getHistoryEventCounterpartiesData,
  } = useHistoryEventsApi();

  const historyEventCounterpartiesData: Ref<ActionDataEntry[]> = asyncComputed<
      ActionDataEntry[]
  >(() => getHistoryEventCounterpartiesData(), []);

  const { scrambleData, scrambleHex } = useScramble();

  const getEventCounterpartyData = (
    event: MaybeRef<{ counterparty: string | null; address?: string | null }>,
  ): ComputedRef<ActionDataEntry | null> => computed(() => {
    const { counterparty, address } = get(event);
    const excludedCounterparty = ['gas'];

    if (counterparty && excludedCounterparty.includes(counterparty))
      return null;

    if (counterparty && !isValidEthAddress(counterparty)) {
      const data = get(historyEventCounterpartiesData).find(
        ({ matcher, identifier }: ActionDataEntry) => {
          if (matcher)
            return matcher(counterparty);

          return identifier.toLowerCase() === counterparty.toLowerCase();
        },
      );

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
      ? scrambleHex(usedLabel)
      : usedLabel;

    return {
      identifier: '',
      label: counterpartyAddress || '',
    };
  });

  const counterparties = useArrayMap(
    historyEventCounterpartiesData,
    ({ identifier }) => identifier,
  );

  return {
    getEventCounterpartyData,
    historyEventCounterpartiesData,
    counterparties,
  };
});
