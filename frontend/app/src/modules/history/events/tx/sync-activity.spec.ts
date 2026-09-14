import { describe, expect, it } from 'vitest';
import {
  accountSyncActivity,
  accountSyncActivityId,
  bankEventsActivity,
  bankEventsActivityId,
  chainSyncActivity,
  chainSyncActivityId,
  exchangeEventsActivity,
  exchangeEventsActivityId,
  onlineEventsActivity,
  onlineEventsActivityId,
} from '@/modules/history/events/tx/sync-activity';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';

/**
 * Literals, not helper-against-descriptor comparisons: the flow names these children before the
 * mechanism submits them, so a change to the id shape has to fail here rather than quietly stop the
 * children being gated by the umbrella that claims them.
 */
describe('sync activity ids', () => {
  it('should key a chain sync by chain alone', () => {
    expect(chainSyncActivity.id({ chain: 'eth' })).toBe('tx-sync:eth');
  });

  it('should key an account sync by chain then address', () => {
    expect(accountSyncActivity.id({ address: '0xabc', chain: 'eth' })).toBe('tx-sync:eth:0xabc');
  });

  it('should make the chain sync id the prefix its accounts sit under', () => {
    const chain = chainSyncActivity.id({ chain: 'eth' });
    expect(accountSyncActivity.id({ address: '0xabc', chain: 'eth' }).startsWith(`${chain}:`)).toBe(true);
  });

  it('should let a chain-wide reader ask for the accounts of one chain', () => {
    expect(accountSyncActivity.partsWithin(['eth'])).toStrictEqual(['eth']);
  });

  it('should key an exchange by location and name', () => {
    expect(exchangeEventsActivity.id({ location: 'kraken', name: 'main' })).toBe('exchange-events:kraken:main');
  });

  it('should give two accounts of one exchange location distinct ids', () => {
    expect(exchangeEventsActivity.id({ location: 'kraken', name: 'main' }))
      .not
      .toBe(exchangeEventsActivity.id({ location: 'kraken', name: 'second' }));
  });

  it('should key a bank connection like an exchange but under its own kind and lane', () => {
    expect(bankEventsActivityId('qonto', 'main')).toBe(makeActivityId(ActivityKind.BANK_EVENTS, 'qonto', 'main'));
    expect(bankEventsActivityId('qonto', 'main')).not.toBe(exchangeEventsActivityId('qonto', 'main'));
    expect(bankEventsActivity.laneOf?.({ location: 'qonto', name: 'main' })).toBe('bank-events:qonto');
  });

  it('should key an online query by its type', () => {
    expect(onlineEventsActivity.id({ queryType: 'eth_withdrawals' })).toBe('online-events:eth_withdrawals');
  });

  it('should give a chain sync and its accounts the same lane family per chain', () => {
    const first = accountSyncActivity.laneOf?.({ address: '0xabc', chain: 'eth' });
    const second = accountSyncActivity.laneOf?.({ address: '0xdef', chain: 'eth' });
    const other = accountSyncActivity.laneOf?.({ address: '0xabc', chain: 'optimism' });

    expect(first).toBe(second);
    expect(first).not.toBe(other);
  });

  it('should route every named helper through its descriptor', () => {
    expect(chainSyncActivityId('eth')).toBe(chainSyncActivity.id({ chain: 'eth' }));
    expect(accountSyncActivityId('eth', '0xabc')).toBe(accountSyncActivity.id({ address: '0xabc', chain: 'eth' }));
    expect(exchangeEventsActivityId('kraken', 'main')).toBe(exchangeEventsActivity.id({ location: 'kraken', name: 'main' }));
    expect(onlineEventsActivityId('eth_withdrawals')).toBe(onlineEventsActivity.id({ queryType: 'eth_withdrawals' }));
  });
});
