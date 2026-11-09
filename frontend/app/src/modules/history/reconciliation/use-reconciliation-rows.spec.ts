import type { ReconciliationAccount, ReconciliationBucket, StatusCounts } from '@/modules/history/reconciliation/schemas';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { reasonLabel } from '@/modules/history/reconciliation/messages';
import {
  accountSummaryFor,
  amountsFor,
  displayStatus,
  headlineFor,
  isHistoryFree,
  latestComparedAt,
  neverCompared,
  sortBuckets,
  statusFilterFor,
  visibleAccounts,
} from '@/modules/history/reconciliation/use-reconciliation-rows';

function counts(overrides: Partial<StatusCounts> = {}): StatusCounts {
  return {
    blocked: 0,
    mismatch: 0,
    notCompared: 0,
    pending: 0,
    reconciled: 0,
    ...overrides,
  };
}

function account(overrides: Partial<ReconciliationAccount> = {}): ReconciliationAccount {
  return {
    counts: counts(),
    historySyncedTo: null,
    isExchange: false,
    lastComparedAt: null,
    lastEventTs: null,
    location: 'ethereum',
    locationLabel: '0xA',
    ...overrides,
  };
}

function bucket(overrides: Partial<ReconciliationBucket> = {}): ReconciliationBucket {
  return {
    asset: 'ETH',
    check: null,
    derivedBalance: null,
    issueId: null,
    lastEventTs: null,
    observedAt: null,
    observedBalance: null,
    protocol: null,
    reasons: [],
    status: 'pending',
    stop: null,
    ...overrides,
  };
}

describe('reconciliation row rules', () => {
  it('should show pending and not_compared under the same Not checked label', () => {
    expect(displayStatus('pending')).toBe('not_checked');
    expect(displayStatus('not_compared')).toBe('not_checked');
    expect(displayStatus('reconciled')).toBe('matches');
  });

  it('should ask only for actionable statuses in the attention view', () => {
    expect(statusFilterFor('attention')).toStrictEqual(['mismatch', 'blocked']);
    expect(statusFilterFor('all')).toBeUndefined();
  });

  it('should keep only accounts with actionable balances in the attention view, urgent first', () => {
    const accounts = [
      account({ counts: counts({ reconciled: 3 }), location: 'bitcoin', locationLabel: 'bc1' }),
      account({ counts: counts({ mismatch: 1 }), location: 'optimism', locationLabel: '0xB' }),
      account({ counts: counts({ blocked: 1 }), location: 'ethereum', locationLabel: '0xC' }),
      account({ counts: counts({ mismatch: 1 }), isExchange: true, location: 'kraken' }),
    ];

    const visible = visibleAccounts(accounts, 'attention');

    expect(visible.map(item => item.location)).toStrictEqual(['optimism', 'ethereum']);
    expect(visibleAccounts(accounts, 'all').map(item => item.location)).toStrictEqual(['optimism', 'ethereum', 'bitcoin']);
  });

  it('should count the balances a Needs-attention account hides', () => {
    const value = account({ counts: counts({ blocked: 1, mismatch: 2, notCompared: 1, pending: 1, reconciled: 4 }) });

    expect(accountSummaryFor(value, 'attention')).toMatchObject({ blocked: 1, hidden: 6, mismatch: 2 });
    expect(accountSummaryFor(value, 'all').hidden).toBe(0);
  });

  it('should show the saved comparison for a verdict and the current values for a pending bucket', () => {
    const checked = bucket({
      check: {
        comparedAt: 1_700_000_100,
        delta: bigNumberify('1.5'),
        derivedBalance: bigNumberify('10'),
        observedAt: 1_700_000_000,
        observedBalance: bigNumberify('11.5'),
      },
      derivedBalance: bigNumberify('99'),
      observedBalance: bigNumberify('88'),
      observedAt: 1_800_000_000,
      status: 'mismatch',
    });
    const pending = bucket({
      derivedBalance: bigNumberify('3'),
      observedBalance: null,
      observedAt: 1_800_000_000,
      status: 'pending',
    });

    const checkedAmounts = amountsFor(checked);
    expect(checkedAmounts.derived?.toFixed()).toBe('10');
    expect(checkedAmounts.observed?.toFixed()).toBe('11.5');
    expect(checkedAmounts.comparedAt).toBe(1_700_000_100);
    expect(checkedAmounts.delta?.toFixed()).toBe('1.5');

    const pendingAmounts = amountsFor(pending);
    expect(pendingAmounts.derived?.toFixed()).toBe('3');
    expect(pendingAmounts.observed).toBeNull();
    expect(pendingAmounts.comparedAt).toBeNull();
    expect(pendingAmounts.delta).toBeNull();
  });

  it('should identify a holding with no events as history-free, and not a native coin', () => {
    expect(isHistoryFree(bucket({ observedBalance: bigNumberify('5'), status: 'mismatch' }))).toBe(true);
    expect(isHistoryFree(bucket({
      derivedBalance: bigNumberify('0'),
      lastEventTs: 1,
      status: 'mismatch',
    }))).toBe(false);
    expect(isHistoryFree(bucket({ status: 'reconciled' }))).toBe(false);
  });

  it('should pick the sentence from the difference sign and the most actionable pending reason', () => {
    expect(reasonLabel(bucket({
      check: {
        comparedAt: 1,
        delta: bigNumberify('1'),
        derivedBalance: bigNumberify('1'),
        observedAt: 1,
        observedBalance: bigNumberify('2'),
      },
      status: 'mismatch',
    }))).toBe('data_issues.reconciliation.reason.mismatch_higher');

    expect(reasonLabel(bucket({
      check: {
        comparedAt: 1,
        delta: bigNumberify('-1'),
        derivedBalance: bigNumberify('2'),
        observedAt: 1,
        observedBalance: bigNumberify('1'),
      },
      status: 'mismatch',
    }))).toBe('data_issues.reconciliation.reason.mismatch_lower');

    expect(reasonLabel(bucket({
      reasons: ['history_not_synced', 'derived_history_stale'],
      status: 'pending',
    }))).toBe('data_issues.reconciliation.reason.history_not_synced');

    expect(reasonLabel(bucket({ reasons: ['rebasing'], status: 'not_compared' })))
      .toBe('data_issues.reconciliation.reason.rebasing');
    expect(reasonLabel(bucket({ reasons: ['future_reason'], status: 'not_compared' })))
      .toBe('data_issues.reconciliation.reason.unknown_not_compared');
  });

  it('should sort mismatches before blocked, then not checked, then matches', () => {
    const rows = [
      bucket({ asset: 'A', status: 'reconciled' }),
      bucket({ asset: 'B', status: 'pending' }),
      bucket({ asset: 'C', status: 'blocked' }),
      bucket({ asset: 'D', status: 'mismatch' }),
    ];

    expect(sortBuckets(rows).map(row => row.status)).toStrictEqual(['mismatch', 'blocked', 'pending', 'reconciled']);
  });
});

describe('reconciliation headline', () => {
  it('should report the mismatch count before anything else', () => {
    expect(headlineFor(counts({ blocked: 2, mismatch: 1, reconciled: 4 })))
      .toStrictEqual({ count: 1, kind: 'mismatch' });
  });

  it('should report stopped processing when nothing mismatches', () => {
    expect(headlineFor(counts({ blocked: 2, reconciled: 4 })))
      .toStrictEqual({ count: 2, kind: 'blocked' });
  });

  it('should say not checked yet instead of all clear', () => {
    expect(headlineFor(counts({ pending: 3 }))).toStrictEqual({ count: 3, kind: 'never' });
  });

  it('should not claim an all-clear while unsupported balances remain', () => {
    expect(headlineFor(counts({ notCompared: 2, reconciled: 4 }))).toStrictEqual({ count: 4, kind: 'partial' });
    expect(headlineFor(counts({ notCompared: 2 }))).toStrictEqual({ count: 2, kind: 'nothing_checkable' });
  });

  it('should claim an all-clear only when every bucket matches', () => {
    expect(headlineFor(counts({ reconciled: 4 }))).toStrictEqual({ count: 4, kind: 'matches' });
  });
});

describe('reconciliation account facts', () => {
  it('should ignore exchange timestamps for the last check', () => {
    expect(latestComparedAt([
      account({ isExchange: true, lastComparedAt: 100 }),
      account({ lastComparedAt: 50 }),
      account({ locationLabel: '0xD', lastComparedAt: 80 }),
    ])).toBe(80);
  });

  it('should call a pending-only report never compared but a not_compared one unsupported', () => {
    expect(neverCompared([account({ counts: counts({ pending: 1 }) })], counts({ pending: 1 }))).toBe(true);
    expect(neverCompared([account({ counts: counts({ notCompared: 1 }) })], counts({ notCompared: 1 }))).toBe(false);
  });
});
