import makeBlockie from 'ethereum-blockies-base64';
import i18n from '@/i18n';
import {
  transactionEventProtocolData,
  transactionEventTypeData,
  transactionEventTypeMapping
} from '@/store/history/consts';
import { EthTransactionEventEntry } from '@/store/history/types';
import { ActionDataEntry } from '@/store/types';
import {
  HistoryEventSubType,
  HistoryEventType,
  TransactionEventProtocol,
  TransactionEventType
} from '@/types/transaction';
import { isValidEthAddress } from '@/utils/text';

export const getEventType = (event: {
  eventType?: string | null;
  eventSubtype?: string | null;
}): TransactionEventType | undefined => {
  const { eventType, eventSubtype } = event;

  const subTypes =
    transactionEventTypeMapping[eventType || HistoryEventType.NONE];
  return subTypes?.[eventSubtype || HistoryEventSubType.NONE] ?? undefined;
};

export const getEventTypeData = (
  event: {
    eventType?: string | null;
    eventSubtype?: string | null;
  },
  showFallbackLabel: boolean = true
): ActionDataEntry => {
  const type = getEventType(event);

  if (type) {
    return get(transactionEventTypeData).find((data: ActionDataEntry) => {
      return data.identifier.toLowerCase() === type.toLowerCase();
    })!;
  }

  const unknownLabel = i18n.t('transactions.events.type.unknown').toString();
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

export const getEventCounterpartyData = (
  event: EthTransactionEventEntry
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

  return {
    identifier: '',
    label: counterparty,
    image: makeBlockie(counterparty)
  };
};
