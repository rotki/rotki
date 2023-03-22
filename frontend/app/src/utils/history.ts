import {
  HistoryEventSubType,
  HistoryEventType,
  TransactionEventProtocol,
  type TransactionEventType
} from '@rotki/common/lib/history/tx-events';
import { isValidEthAddress } from '@/utils/text';
import { type EthTransactionEventEntry } from '@/types/history/tx';
import { uniqueStrings } from '@/utils/data';
import { type EntryMeta, type EntryWithMeta } from '@/types/history/meta';
import { type Collection } from '@/types/collection';
import { transactionEventTypeMapping } from '@/data/transaction-event-mapping';
import { type ActionDataEntry } from '@/types/action';

export const getEventType = (event: {
  eventType?: string | null;
  eventSubtype?: string | null;
}): TransactionEventType | undefined => {
  const { eventType, eventSubtype } = event;

  const subTypes =
    transactionEventTypeMapping[eventType || HistoryEventType.NONE];
  return subTypes?.[eventSubtype || HistoryEventSubType.NONE] ?? undefined;
};

export const useEventTypeData = createSharedComposable(() => {
  const { tc } = useI18n();
  const { transactionEventTypeData } = useTransactionEventTypeData();
  const getEventTypeData = (
    event: {
      eventType?: string | null;
      eventSubtype?: string | null;
    },
    showFallbackLabel = true
  ): ActionDataEntry => {
    const type = getEventType(event);

    if (type) {
      return get(transactionEventTypeData).find((data: ActionDataEntry) => {
        return data.identifier.toLowerCase() === type.toLowerCase();
      })!;
    }

    const unknownLabel = tc('transactions.events.type.unknown');
    const label = showFallbackLabel
      ? event.eventSubtype || event.eventType || unknownLabel
      : unknownLabel;

    return {
      identifier: '',
      label,
      icon: 'mdi-help',
      color: 'red'
    };
  };

  return {
    getEventTypeData
  };
});

export const getEventCounterpartyData = (
  event: EthTransactionEventEntry,
  scrambler?: (hex: string) => string
): ActionDataEntry | null => {
  const { counterparty } = event;

  const excludedCounterparty = [TransactionEventProtocol.GAS];

  if (
    !counterparty ||
    excludedCounterparty.includes(counterparty as TransactionEventProtocol)
  ) {
    return null;
  }

  if (!isValidEthAddress(counterparty)) {
    const data = get(transactionEventProtocolData).find(
      (data: ActionDataEntry) => {
        if (data.matcher) {
          return data.matcher(counterparty);
        }
        return data.identifier.toLowerCase() === counterparty.toLowerCase();
      }
    );

    if (data) {
      return {
        ...data,
        label: counterparty.toUpperCase()
      };
    }

    return {
      identifier: '',
      label: counterparty,
      icon: 'mdi-help',
      color: 'red'
    };
  }

  const counterpartyAddress = scrambler?.(counterparty) ?? counterparty;

  return {
    identifier: '',
    label: counterpartyAddress
  };
};

export function mapCollectionEntriesWithMeta<T>(
  collection: Collection<EntryWithMeta<T>>
): Collection<T & EntryMeta> {
  const entries = collection.data.map(data => {
    return transformEntryWithMeta<T>(data);
  });
  return {
    ...collection,
    data: entries
  };
}

export function transformEntryWithMeta<T>(
  data: EntryWithMeta<T>
): T & EntryMeta {
  const { entry, ...entriesMeta } = data;

  return {
    ...entry,
    ...entriesMeta
  };
}

export function filterAddressesFromWords(words: string[]): string[] {
  return words.filter(uniqueStrings).filter(isValidEthAddress);
}
