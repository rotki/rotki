import type { BucketStatus, ReconciliationAccount, ReconciliationBucket, ReconciliationResponse, StatusCounts } from '@/modules/history/reconciliation/schemas';
import { get } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBucketReconciliation } from '@/modules/history/reconciliation/use-bucket-reconciliation';
import { useBucketReconciliationStore } from '@/modules/history/reconciliation/use-bucket-reconciliation-store';
import { reconciliationAccountKey } from '@/modules/history/reconciliation/use-reconciliation-rows';

const fetchSummary = vi.fn<() => Promise<ReconciliationResponse>>();
const fetchAccount = vi.fn<(request: Record<string, unknown>) => Promise<ReconciliationAccount | undefined>>();

vi.mock('@/modules/history/reconciliation/api/use-bucket-reconciliation-api', () => ({
  ACCOUNT_PAGE_SIZE: 50,
  MAX_ACCOUNT_BUCKETS: 500,
  useBucketReconciliationApi: (): Record<string, unknown> => ({
    fetchAccount,
    fetchSummary,
  }),
}));

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

function bucket(asset: string): ReconciliationBucket {
  return {
    asset,
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
  };
}

function response(overrides: Partial<ReconciliationResponse> = {}): ReconciliationResponse {
  return {
    accounts: [],
    bucketsTotal: 0,
    processing: false,
    stale: false,
    totals: counts(),
    ...overrides,
  };
}

function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolveFn) => {
    resolve = resolveFn;
  });
  return { promise, resolve };
}

describe('useBucketReconciliation', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.resetAllMocks();
  });

  it('should let only the newest summary request write the store', async () => {
    const first = deferred<ReconciliationResponse>();
    const second = deferred<ReconciliationResponse>();
    fetchSummary.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);

    const { refreshSummary, totals } = useBucketReconciliation();
    const firstRun = refreshSummary();
    const secondRun = refreshSummary();

    second.resolve(response({ totals: counts({ mismatch: 2 }) }));
    await secondRun;
    first.resolve(response({ totals: counts({ mismatch: 9 }) }));
    await firstRun;

    expect(get(totals).mismatch).toBe(2);
    expect(useBucketReconciliationStore().summaryFailed).toBe(false);
  });

  it('should mark a failed refresh without dropping the previous summary', async () => {
    fetchSummary
      .mockResolvedValueOnce(response({ totals: counts({ reconciled: 4 }) }))
      .mockRejectedValueOnce(new Error('boom'));
    const { refreshSummary, summaryFailed, totals } = useBucketReconciliation();

    await refreshSummary();
    await refreshSummary();

    expect(get(summaryFailed)).toBe(true);
    expect(get(totals).reconciled).toBe(4);
  });

  it('should fetch an account once per status filter and reuse it afterwards', async () => {
    fetchAccount.mockResolvedValue(account({ buckets: [], pagination: { limit: 50, offset: 0, total: 0 } }));
    const { ensureAccount } = useBucketReconciliation();
    const eth = account();

    await ensureAccount(eth, ['mismatch', 'blocked']);
    await ensureAccount(eth, ['blocked', 'mismatch']);
    expect(fetchAccount).toHaveBeenCalledTimes(1);
    expect(fetchAccount.mock.calls[0][0]).toMatchObject({ status: ['mismatch', 'blocked'] });

    await ensureAccount(eth);
    expect(fetchAccount).toHaveBeenCalledTimes(2);
    expect(fetchAccount.mock.calls[1][0].status).toBeUndefined();
  });

  it('should send the empty label to scope a null-label account', async () => {
    fetchAccount.mockResolvedValue(account({
      buckets: [],
      location: 'aave',
      locationLabel: null,
      pagination: { limit: 50, offset: 0, total: 0 },
    }));
    const { ensureAccount } = useBucketReconciliation();

    await ensureAccount(account({ location: 'aave', locationLabel: null }));

    expect(fetchAccount.mock.calls[0][0]).toMatchObject({ location: 'aave', locationLabel: '' });
  });

  it('should not let a slow old account response overwrite a retry', async () => {
    const first = deferred<ReconciliationAccount | undefined>();
    const second = deferred<ReconciliationAccount | undefined>();
    fetchAccount.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const { ensureAccount, retryAccount } = useBucketReconciliation();
    const eth = account();

    const initial = ensureAccount(eth);
    const retried = retryAccount(eth);

    second.resolve(account({
      buckets: [bucket('NEW')],
      pagination: { limit: 50, offset: 0, total: 1 },
    }));
    await retried;
    first.resolve(account({
      buckets: [bucket('OLD')],
      pagination: { limit: 50, offset: 0, total: 1 },
    }));
    await initial;

    const detail = useBucketReconciliationStore().accountState(reconciliationAccountKey('ethereum', '0xA'));
    expect(detail?.buckets.map(item => item.asset)).toStrictEqual(['NEW']);
  });

  it.each([
    { startsFiltered: true, oldFinishesFirst: true },
    { startsFiltered: true, oldFinishesFirst: false },
    { startsFiltered: false, oldFinishesFirst: true },
    { startsFiltered: false, oldFinishesFirst: false },
  ])('should replace in-flight rows on a view switch ($startsFiltered, $oldFinishesFirst)', async ({ startsFiltered, oldFinishesFirst }) => {
    const attention: BucketStatus[] = ['mismatch', 'blocked'];
    const previousStatuses = startsFiltered ? attention : undefined;
    const nextStatuses = startsFiltered ? undefined : attention;
    const first = deferred<ReconciliationAccount | undefined>();
    const second = deferred<ReconciliationAccount | undefined>();
    const eth = account();
    const store = useBucketReconciliationStore();
    store.setSummary(response({ accounts: [eth] }));
    fetchAccount.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const { ensureAccount, reloadAccounts, loadMore } = useBucketReconciliation();
    const initial = ensureAccount(eth, previousStatuses);
    const switched = reloadAccounts(nextStatuses);
    const oldRows = account({
      buckets: [bucket('OLD')],
      pagination: { limit: 50, offset: 0, total: 1 },
    });
    const newRows = account({
      buckets: [bucket('NEW'), bucket('CURRENT')],
      pagination: { limit: 50, offset: 0, total: 3 },
    });

    async function finishOld(): Promise<void> {
      first.resolve(oldRows);
      await initial;
    }

    async function finishNew(): Promise<void> {
      second.resolve(newRows);
      await switched;
    }

    const completions = oldFinishesFirst ? [finishOld, finishNew] : [finishNew, finishOld];
    await completions[0]();
    await completions[1]();

    const key = reconciliationAccountKey('ethereum', '0xA');
    expect(store.accountState(key)?.buckets.map(item => item.asset)).toStrictEqual(['NEW', 'CURRENT']);
    expect(store.accountState(key)?.pagination.total).toBe(3);
    expect(store.accountState(key)?.statusKey).toBe(startsFiltered ? 'all' : 'blocked,mismatch');

    fetchAccount.mockResolvedValueOnce(account({
      buckets: [bucket('LAST')],
      pagination: { limit: 50, offset: 2, total: 3 },
    }));
    await loadMore(eth, nextStatuses);
    expect(fetchAccount.mock.calls[2][0]).toMatchObject({ offset: 2, status: nextStatuses });
    expect(store.accountState(key)?.buckets.map(item => item.asset)).toStrictEqual(['NEW', 'CURRENT', 'LAST']);
  });

  it('should append the next page without duplicating a row that moved between reads', async () => {
    const paged = account({
      buckets: [bucket('A'), bucket('B')],
      pagination: { limit: 50, offset: 0, total: 3 },
    });
    const next = account({
      buckets: [bucket('B'), bucket('C')],
      pagination: { limit: 50, offset: 2, total: 3 },
    });
    fetchAccount.mockResolvedValueOnce(paged).mockResolvedValueOnce(next);
    const { ensureAccount, loadMore } = useBucketReconciliation();
    const eth = account();

    await ensureAccount(eth);
    await loadMore(eth);

    const detail = useBucketReconciliationStore().accountState(reconciliationAccountKey('ethereum', '0xA'));
    expect(detail?.buckets.map(item => item.asset)).toStrictEqual(['A', 'B', 'C']);
    expect(fetchAccount.mock.calls[1][0]).toMatchObject({ offset: 2 });
  });
});
