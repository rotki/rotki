import type { BucketStatus, ReconciliationAccount, ReconciliationBucket, ReconciliationResponse, StatusCounts } from '@/modules/history/reconciliation/schemas';
import { get } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ZodError } from 'zod';
import { isRetryableFailure } from '@/modules/core/api/request-result';
import { createStatusError } from '@/modules/core/api/response-handlers';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
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

  it('should mark the report unavailable, not failed, when the backend runs without the accounting update', async () => {
    fetchSummary
      .mockResolvedValueOnce(response({ totals: counts({ mismatch: 1 }) }))
      .mockRejectedValueOnce(createStatusError(404, 'Historical balance reconciliation is disabled', {
        cause: 'not_found',
        message: 'Historical balance reconciliation is disabled',
        result: null,
      }));
    const { attention, refreshSummary, summaryFailed, summaryUnavailable } = useBucketReconciliation();

    await refreshSummary();
    await refreshSummary();

    expect(get(summaryUnavailable)).toBe(true);
    expect(get(summaryFailed)).toBe(false);
    expect(get(attention)).toBe(0);
  });

  it('should treat a failure with another cause as a failed refresh', async () => {
    fetchSummary.mockRejectedValueOnce(createStatusError(500, 'boom', { cause: 'internal', message: 'boom', result: null }));
    const { refreshSummary, summaryFailed, summaryUnavailable } = useBucketReconciliation();

    await refreshSummary();

    expect(get(summaryFailed)).toBe(true);
    expect(get(summaryUnavailable)).toBe(false);
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

  it('should mark the report unavailable when an account request finds the backend without the accounting update', async () => {
    fetchSummary.mockResolvedValueOnce(response({ accounts: [account()], totals: counts({ mismatch: 1 }) }));
    fetchAccount.mockRejectedValueOnce(createStatusError(404, 'Historical balance reconciliation is disabled', {
      cause: 'not_found',
      message: 'Historical balance reconciliation is disabled',
      result: null,
    }));
    const { ensureAccount, refreshSummary, summaryUnavailable } = useBucketReconciliation();

    await refreshSummary();
    await ensureAccount(account());

    expect(get(summaryUnavailable)).toBe(true);
    expect(useBucketReconciliationStore().accountState(reconciliationAccountKey('ethereum', '0xA'))).toBeUndefined();
  });

  it('should ask for the summary again when an account\'s counts no longer match it', async () => {
    fetchSummary
      .mockResolvedValueOnce(response({ accounts: [account({ counts: counts({ mismatch: 1 }) })], totals: counts({ mismatch: 1 }) }))
      .mockResolvedValueOnce(response({ accounts: [account({ counts: counts({ pending: 1 }) })], totals: counts({ pending: 1 }) }));
    fetchAccount.mockResolvedValue(account({
      buckets: [],
      counts: counts({ pending: 1 }),
      pagination: { limit: 50, offset: 0, total: 0 },
    }));
    const { attention, ensureAccount, refreshSummary } = useBucketReconciliation();

    await refreshSummary();
    await ensureAccount(account({ counts: counts({ mismatch: 1 }) }), ['mismatch', 'blocked']);

    expect(fetchSummary).toHaveBeenCalledTimes(2);
    expect(get(attention)).toBe(0);
  });

  it('should not ask for the summary again when an account agrees with it', async () => {
    fetchSummary.mockResolvedValueOnce(response({ accounts: [account({ counts: counts({ mismatch: 1 }) })], totals: counts({ mismatch: 1 }) }));
    fetchAccount.mockResolvedValue(account({
      buckets: [],
      counts: counts({ mismatch: 1 }),
      pagination: { limit: 50, offset: 0, total: 0 },
    }));
    const { ensureAccount, refreshSummary } = useBucketReconciliation();

    await refreshSummary();
    await ensureAccount(account({ counts: counts({ mismatch: 1 }) }));

    expect(fetchSummary).toHaveBeenCalledOnce();
  });

  it('should keep any other account failure whole on the account row', async () => {
    const failure = new Error('boom');
    fetchAccount.mockRejectedValueOnce(failure);
    const { ensureAccount, summaryUnavailable } = useBucketReconciliation();

    await ensureAccount(account());

    expect(get(summaryUnavailable)).toBe(false);
    expect(useBucketReconciliationStore().accountState(reconciliationAccountKey('ethereum', '0xA'))?.error).toBe(failure);
  });

  it('should keep the backend failure whole, so its message and cause reach the page', async () => {
    const failure = createStatusError(500, 'boom', { cause: 'internal', message: 'boom', result: null });
    fetchSummary.mockRejectedValueOnce(failure);
    const { refreshSummary, summaryFailure } = useBucketReconciliation();

    await refreshSummary();

    expect(get(summaryFailure)).toBe(failure);
  });

  it('should word a response that does not parse and offer no retry, since asking again returns the same answer', async () => {
    fetchSummary.mockRejectedValueOnce(new ZodError([]));
    const { refreshSummary, summaryFailure } = useBucketReconciliation();

    await refreshSummary();

    const failure = get(summaryFailure);
    expect(getErrorMessage(failure)).toBe('data_issues.reconciliation.failure.unexpected_response');
    expect(isRetryableFailure(failure)).toBe(false);
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

  it('should keep loaded pages visible during refresh and paginate from the refreshed rows', async () => {
    const eth = account();
    const store = useBucketReconciliationStore();
    const key = reconciliationAccountKey('ethereum', '0xA');
    const original = Array.from({ length: 150 }, (_, index) => bucket(`OLD-${index}`));
    store.setSummary(response({ accounts: [eth] }));
    const { ensureAccount, loadMore, reloadAccounts } = useBucketReconciliation();
    for (let offset = 0; offset < 150; offset += 50) {
      fetchAccount.mockResolvedValueOnce(account({
        buckets: original.slice(offset, offset + 50),
        pagination: { limit: 50, offset, total: 200 },
      }));
      if (offset === 0)
        await ensureAccount(eth);
      else
        await loadMore(eth);
    }

    const refresh = deferred<ReconciliationAccount | undefined>();
    fetchAccount.mockReturnValueOnce(refresh.promise);
    const refreshing = reloadAccounts();

    expect(store.accountState(key)?.buckets).toEqual(original);
    expect(store.accountState(key)?.loading).toBe(true);
    expect(fetchAccount).toHaveBeenLastCalledWith(expect.objectContaining({ limit: 150, offset: 0 }));

    const updated = Array.from({ length: 150 }, (_, index) => bucket(`NEW-${index}`));
    refresh.resolve(account({
      buckets: updated,
      pagination: { limit: 150, offset: 0, total: 151 },
    }));
    await refreshing;
    expect(store.accountState(key)?.buckets).toEqual(updated);
    expect(store.accountState(key)?.loading).toBe(false);

    fetchAccount.mockResolvedValueOnce(account({
      buckets: [bucket('LAST')],
      pagination: { limit: 50, offset: 150, total: 151 },
    }));
    await loadMore(eth);
    expect(fetchAccount).toHaveBeenLastCalledWith(expect.objectContaining({ limit: 50, offset: 150 }));
    expect(store.accountState(key)?.buckets).toEqual([...updated, bucket('LAST')]);
  });

  it('should discard previously loaded rows when refreshing with a different filter', async () => {
    const eth = account();
    const store = useBucketReconciliationStore();
    const key = reconciliationAccountKey('ethereum', '0xA');
    store.setSummary(response({ accounts: [eth] }));
    fetchAccount.mockResolvedValueOnce(account({
      buckets: [bucket('OLD')],
      pagination: { limit: 50, offset: 0, total: 1 },
    }));
    const { ensureAccount, reloadAccounts } = useBucketReconciliation();
    await ensureAccount(eth);
    const refresh = deferred<ReconciliationAccount | undefined>();
    fetchAccount.mockReturnValueOnce(refresh.promise);
    const refreshing = reloadAccounts(['mismatch', 'blocked']);

    expect(store.accountState(key)?.buckets).toEqual([]);
    expect(store.accountState(key)?.loaded).toBe(false);
    expect(fetchAccount).toHaveBeenLastCalledWith(expect.objectContaining({
      limit: 50,
      offset: 0,
      status: ['mismatch', 'blocked'],
    }));
    refresh.resolve(account({
      buckets: [bucket('NEW')],
      pagination: { limit: 50, offset: 0, total: 1 },
    }));
    await refreshing;
    expect(store.accountState(key)?.buckets).toEqual([bucket('NEW')]);
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
