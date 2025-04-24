import { groupSwaps } from '@/modules/history/events/utils';
import {
  type EvmHistoryEvent,
  type EvmSwapEvent,
  HistoryEventAccountingRuleStatus,
  type HistoryEventEntry,
  type HistoryEventMeta,
} from '@/types/history/events';
import { type BigNumber, bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { describe, expect, it } from 'vitest';

type SwapWithMeta = EvmSwapEvent & HistoryEventMeta;

interface CommonData extends Pick<
  SwapWithMeta,
    'address' | 'counterparty' | 'identifier' | 'location' | 'locationLabel' | 'timestamp' | 'txHash'
> {}

interface AssetData {
  asset: string;
  amount: BigNumber;
}

function createSwapEvents(
  commonData: CommonData,
  assets: {
    spend: AssetData;
    receive: AssetData;
    fee?: AssetData;
  },
  startingSequenceIndex = 0,
): [SwapWithMeta, SwapWithMeta] | [SwapWithMeta, SwapWithMeta, SwapWithMeta] {
  if (!commonData || !assets.spend || !assets.receive) {
    throw new Error('Missing required parameters for swap creation');
  }

  const eventIdentifier = `1${commonData.txHash}`;

  const createBaseEvent = (sequenceIndex: number): Omit<SwapWithMeta, 'amount' | 'asset' | 'eventSubtype'> => ({
    address: commonData.address,
    counterparty: commonData.counterparty || 'some counterparty',
    entryType: 'evm swap event',
    eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.HAS_RULE,
    eventIdentifier,
    eventType: 'trade',
    extraData: null,
    identifier: commonData.identifier++,
    location: commonData.location || 'ethereum',
    locationLabel: commonData.locationLabel,
    product: null,
    sequenceIndex: startingSequenceIndex + sequenceIndex,
    timestamp: commonData.timestamp,
    txHash: commonData.txHash,
  });

  const spendEvent: SwapWithMeta = {
    ...createBaseEvent(0),
    amount: assets.spend.amount,
    asset: assets.spend.asset,
    eventSubtype: 'spend',
  };

  const receiveEvent: SwapWithMeta = {
    ...createBaseEvent(1),
    amount: assets.receive.amount,
    asset: assets.receive.asset,
    eventSubtype: 'receive',
  };

  if (assets.fee) {
    const feeEvent: SwapWithMeta = {
      ...createBaseEvent(2),
      amount: assets.fee.amount,
      asset: assets.fee.asset,
      eventSubtype: 'fee',
    };
    return [spendEvent, receiveEvent, feeEvent];
  }

  return [spendEvent, receiveEvent];
}

const commonData: CommonData = {
  address: '0xA090e606E30bD747d4E6245a1517EbE430F0057e',
  counterparty: 'aave',
  identifier: 2738,
  location: 'ethereum',
  locationLabel: '0x6e15887E2CEC81434C16D587709f64603b39b545',
  timestamp: 1745328427000,
  txHash: '0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f',
};

const approvalEvent: EvmHistoryEvent & HistoryEventMeta = {
  ...commonData,
  amount: bigNumberify(100),
  asset: 'ETH',
  entryType: HistoryEventEntryType.EVM_EVENT,
  eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.HAS_RULE,
  eventIdentifier: `1${commonData.txHash}`,
  eventSubtype: 'approve',
  eventType: 'informational',
  product: null,
  sequenceIndex: 3,
};

describe('grouping swaps in event group', () => {
  it('should group different swaps', () => {
    const events: HistoryEventEntry[] = [];
    const firstSwap = createSwapEvents(commonData, {
      receive: {
        amount: bigNumberify('0.22'),
        asset: 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
      },
      spend: {
        amount: bigNumberify('0.0033'),
        asset: 'ETH',
      },
    });
    events.push(...firstSwap);

    const nextSequenceIndex = Number(events.at(-1)?.sequenceIndex ?? 0);
    const secondSwap = createSwapEvents(commonData, {
      fee: {
        amount: bigNumberify('0.0001'),
        asset: 'ETH',
      },
      receive: {
        amount: bigNumberify('0.21'),
        asset: 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
      },
      spend: {
        amount: bigNumberify('0.0032'),
        asset: 'ETH',
      },
    }, nextSequenceIndex + 1);
    events.push(...secondSwap);

    const groupedEvents = groupSwaps(events);
    expect(groupedEvents).toHaveLength(2);
    expect(groupedEvents).toMatchObject([{
      events: firstSwap,
      type: 'swap',
    }, {
      events: secondSwap,
      type: 'swap',
    }]);
  });

  it('should group swaps and keep evm events as they are', () => {
    const events: HistoryEventEntry[] = [];
    const firstSwap = createSwapEvents(commonData, {
      receive: {
        amount: bigNumberify('0.24'),
        asset: 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
      },
      spend: {
        amount: bigNumberify('0.0031'),
        asset: 'ETH',
      },
    });

    const approvalEventRecord = {
      ...approvalEvent,
      sequenceIndex: Number(events.at(-1)?.sequenceIndex ?? 0) + 1,
    };
    events.push(...firstSwap, approvalEventRecord);

    const nextSequenceIndex = Number(events.at(-1)?.sequenceIndex ?? 0);
    const secondSwap = createSwapEvents(commonData, {
      fee: {
        amount: bigNumberify('0.0001'),
        asset: 'ETH',
      },
      receive: {
        amount: bigNumberify('0.251'),
        asset: 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
      },
      spend: {
        amount: bigNumberify('0.00399'),
        asset: 'ETH',
      },
    }, nextSequenceIndex + 1);
    events.push(...secondSwap);

    const groupedEvents = groupSwaps(events);
    expect(groupedEvents).toHaveLength(3);
    expect(groupedEvents).toMatchObject([{
      events: firstSwap,
      type: 'swap',
    }, {
      event: approvalEventRecord,
      type: 'evm',
    }, {
      events: secondSwap,
      type: 'swap',
    }]);
  });
});
