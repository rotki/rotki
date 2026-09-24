import { describe, expect, it } from 'vitest';
import { accountAddActivity, EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
import { decodeActivity, targetedDecodeActivity } from '@/modules/history/events/tx/decode-activity';
import { accountSyncActivity, bankEventsActivity, chainSyncActivity, exchangeEventsActivity } from '@/modules/history/events/tx/sync-activity';
import { activitySubject } from './activity-subject';
import { type Activity, type ActivityId, ActivityKind, ActivityPart, ActivitySourceType, ActivityStatus, makeActivityId } from './core/types';

function activity(id: ActivityId, kind: ActivityKind): Activity {
  return {
    cancellable: false,
    id,
    kind,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status: ActivityStatus.RUNNING,
    title: kind,
  };
}

const ADDRESS = '0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1';

describe('activitySubject', () => {
  it('should name the chain of a chain sync and the account of an account sync', () => {
    expect(activitySubject(activity(chainSyncActivity.id({ chain: 'eth' }), ActivityKind.TX_SYNC))).toEqual({ chain: 'eth' });
    expect(activitySubject(activity(accountSyncActivity.id({ address: ADDRESS, chain: 'eth' }), ActivityKind.TX_SYNC)))
      .toEqual({ address: ADDRESS, chain: 'eth' });
  });

  it('should name the chain of a whole decode and of a targeted one', () => {
    expect(activitySubject(activity(decodeActivity.id({ chain: 'optimism', ignoreCache: true }), ActivityKind.TX_DECODING)))
      .toEqual({ chain: 'optimism' });
    expect(activitySubject(activity(targetedDecodeActivity.id({ chain: 'base', txRefs: ['0xb', '0xa'] }), ActivityKind.TX_DECODING)))
      .toEqual({ chain: 'base' });
  });

  it('should name the location of an exchange or a bank', () => {
    const connection = { location: 'kraken', name: 'main' };

    expect(activitySubject(activity(exchangeEventsActivity.id(connection), ActivityKind.EXCHANGE_EVENTS))).toEqual({ location: 'kraken' });
    expect(activitySubject(activity(bankEventsActivity.id({ location: 'monerium', name: 'iban' }), ActivityKind.BANK_EVENTS)))
      .toEqual({ location: 'monerium' });
    expect(activitySubject(activity(makeActivityId(ActivityKind.EXCHANGE_BALANCES, 'binance'), ActivityKind.EXCHANGE_BALANCES)))
      .toEqual({ location: 'binance' });
  });

  it('should name the chain of a balance job, with or without detection, but not of the run over several chains', () => {
    const balances = (...parts: string[]): Activity => activity(makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, ...parts), ActivityKind.BLOCKCHAIN_BALANCES);

    expect(activitySubject(balances('eth'))).toEqual({ chain: 'eth' });
    expect(activitySubject(balances('eth', ActivityPart.DETECT, 'digest'))).toEqual({ chain: 'eth' });
    expect(activitySubject(balances(ActivityPart.RUN, 'digest', 'user'))).toBeUndefined();
  });

  it('should name the account of a token detection', () => {
    const detection = activity(makeActivityId(ActivityKind.TOKEN_DETECTION, 'eth', ADDRESS), ActivityKind.TOKEN_DETECTION);

    expect(activitySubject(detection)).toEqual({ address: ADDRESS, chain: 'eth' });
  });

  it('should name the account of a single addition, without a chain for the every-EVM-chain one', () => {
    const addition = (chain: string): Activity =>
      activity(accountAddActivity.id({ chain, target: { address: ADDRESS, kind: 'address' } }), ActivityKind.ACCOUNTS);

    expect(activitySubject(addition('optimism'))).toEqual({ address: ADDRESS, chain: 'optimism' });
    expect(activitySubject(addition(EVM_PSEUDO_CHAIN))).toEqual({ address: ADDRESS });
  });

  it('should name nothing for a bulk addition, whose id holds several addresses', () => {
    const bulk = accountAddActivity.id({ chain: 'eth', target: { addresses: [ADDRESS, '0xb'], kind: 'addresses' } });

    expect(activitySubject(activity(bulk, ActivityKind.ACCOUNTS))).toBeUndefined();
    expect(activitySubject(activity(accountAddActivity.batchId(['eth']), ActivityKind.ACCOUNTS))).toBeUndefined();
  });

  it('should name nothing for an id its kind\'s producer never mints', () => {
    expect(activitySubject(activity(makeActivityId(ActivityKind.TX_SYNC, ActivityPart.RUN, 'all', 'x'), ActivityKind.TX_SYNC))).toBeUndefined();
    expect(activitySubject(activity(makeActivityId(ActivityKind.PRICES, ActivityPart.LATEST), ActivityKind.PRICES))).toBeUndefined();
  });
});
