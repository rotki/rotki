import makeBlockie from 'ethereum-blockies-base64';
import i18n from '@/i18n';
import {
  ActionDataEntry,
  transactionEventProtocolData,
  transactionEventTypeData,
  transactionEventTypeMapping
} from '@/store/history/consts';
import { EthTransactionEventEntry } from '@/store/history/types';
import {
  TransactionEventProtocol,
  TransactionEventType
} from '@/types/transaction';

export const getEventType = (
  event: EthTransactionEventEntry
): TransactionEventType | undefined => {
  const { eventType, eventSubtype } = event;

  const subTypes = transactionEventTypeMapping[eventType || 'null'];
  return subTypes?.[eventSubtype || 'null'] ?? undefined;
};

export const getEventTypeData = (
  event: EthTransactionEventEntry
): ActionDataEntry => {
  const type = getEventType(event);

  if (type) {
    return transactionEventTypeData.find((data: ActionDataEntry) => {
      return data.identifier.toLowerCase() === type.toLowerCase();
    })!;
  }

  return {
    identifier: '',
    label:
      event.eventSubtype ||
      event.eventType ||
      i18n.t('transactions.event_type.unknown').toString(),
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

  const isAddress = counterparty.startsWith('0x') && counterparty.length >= 42;

  if (!isAddress) {
    const data = transactionEventProtocolData.find((data: ActionDataEntry) => {
      if (data.matcher) {
        return data.matcher(counterparty);
      }
      return data.identifier.toLowerCase() === counterparty.toLowerCase();
    });

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
