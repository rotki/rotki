import type { useLocations } from '@/modules/core/common/use-locations';
import type { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import type { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import type { UseBucketTraceApiReturn } from '@/modules/history/reconciliation/api/use-bucket-trace-api';
import type { BucketTraceRequest, BucketTraceResponse, BucketTraceRow, InspectedBucket } from '@/modules/history/reconciliation/schemas';
import { bigNumberify, Blockchain } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, defineComponent } from 'vue';
import { ZodError } from 'zod';
import { RequestCancelledError } from '@/modules/core/api/request-queue/errors';
import BucketTraceDrawer from '@/modules/history/reconciliation/components/BucketTraceDrawer.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { fetchBucketTrace } = vi.hoisted(() => ({
  fetchBucketTrace: vi.fn<(req: BucketTraceRequest) => Promise<BucketTraceResponse>>(),
}));

vi.mock('@/modules/history/reconciliation/api/use-bucket-trace-api', () => ({
  BUCKET_TRACE_PAGE_SIZE: 50,
  useBucketTraceApi: (): UseBucketTraceApiReturn => ({ fetchBucketTrace }),
}));

vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: (): ReturnType<typeof useLocations> => createMock<ReturnType<typeof useLocations>>({
    useLocationData: () => computed(() => ({ detailPath: '/balances/blockchain', identifier: 'ethereum', image: '', name: 'Ethereum' })),
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): ReturnType<typeof useSupportedChains> => createMock<ReturnType<typeof useSupportedChains>>({
    matchChain: (location: string) => (location === 'ethereum' ? Blockchain.ETH : undefined),
  }),
}));

vi.mock('@/modules/history/events/mapping/use-history-event-counterparty-mappings', () => ({
  useHistoryEventCounterpartyMappings: (): ReturnType<typeof useHistoryEventCounterpartyMappings> =>
    createMock<ReturnType<typeof useHistoryEventCounterpartyMappings>>({
      getBaseCounterpartyData: (protocol: string) => (protocol === 'aave-v3'
        ? { identifier: 'aave-v3', image: '', label: 'Aave V3' }
        : undefined),
    }),
}));

const RouterLinkStub = defineComponent({
  name: 'RouterLink',
  props: { to: { type: [Object, String], required: true } },
  template: '<a><slot /></a>',
});

const DrawerStub = defineComponent({
  name: 'RuiNavigationDrawer',
  props: { modelValue: { type: Boolean, default: false } },
  template: '<div v-if="modelValue"><slot /></div>',
});

const ASSET = 'eip155:1/erc20:0x6df1C1E379bC5a00a7b4C6e67A203333772f45A8';
const ACCOUNT = '0x006a3aD7251db5D12992B62cce26252ac58492Dd';

const TARGET: InspectedBucket = {
  account: {
    counts: { blocked: 0, mismatch: 0, notCompared: 0, pending: 1, reconciled: 0 },
    historySyncedTo: 1_795_185_791,
    isExchange: false,
    lastComparedAt: 1_795_186_075,
    lastEventTs: 1_794_969_035_000,
    location: 'ethereum',
    locationLabel: ACCOUNT,
  },
  bucket: {
    asset: ASSET,
    check: null,
    derivedBalance: bigNumberify('22060.968451'),
    issueId: null,
    issueKind: null,
    lastEventTs: 1_794_969_035_000,
    observedAt: 1_795_186_889,
    observedBalance: bigNumberify('22067.18699'),
    protocol: null,
    reasons: ['observation_superseded'],
    status: 'pending',
    stop: null,
  },
};

function makeRow(id: number, overrides: Partial<BucketTraceRow> = {}): BucketTraceRow {
  return {
    balanceAfter: bigNumberify('5000'),
    balanceBefore: bigNumberify('0'),
    counterparty: 'aave-v3',
    customized: false,
    direction: 'in',
    eventAsset: ASSET,
    eventIdentifier: id,
    eventSubtype: 'receive',
    eventType: 'receive',
    groupIdentifier: `0xtx${id}`,
    rebaseYield: null,
    rule: 'receive',
    sequenceIndex: id,
    signedAmount: bigNumberify('5000'),
    status: 'applied',
    storedBalance: bigNumberify('5000'),
    timestampMs: 1_794_900_000_000 + id,
    ...overrides,
  };
}

function traceResponse(overrides: Partial<BucketTraceResponse> = {}): BucketTraceResponse {
  return {
    pagination: { limit: 50, offset: 0, total: 2, truncated: false },
    rows: [
      makeRow(101, { groupIdentifier: '0xtx1', sequenceIndex: 0 }),
      makeRow(102, { groupIdentifier: '0xtx2', sequenceIndex: 1, status: 'stop' }),
    ],
    summary: {
      awaitingRebaseReconciliation: false,
      derivedBalancesStale: false,
      effectsTotal: 2,
      finalBalance: bigNumberify('22060.968451'),
      rebasingAsset: false,
      skippedAfterStop: 0,
      stopRowIndex: null,
      storedBalanceMismatches: 0,
    },
    ...overrides,
  };
}

function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

function mountDrawer(target: InspectedBucket = TARGET, modelValue = true): VueWrapper {
  const pinia = createPinia();
  setActivePinia(pinia);
  return mount(BucketTraceDrawer, {
    global: {
      plugins: [pinia, createRuiPlugin({})],
      stubs: {
        AssetDetails: true,
        CounterpartyDisplay: true,
        DateDisplay: true,
        HashLink: true,
        ReconciliationAmount: true,
        RouterLink: RouterLinkStub,
        RuiNavigationDrawer: DrawerStub,
        TimeAgoDisplay: true,
      },
    },
    props: { modelValue, target },
  });
}

describe('bucketTraceDrawer', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('should render chronological trace rows with localized statuses, protocol label, mismatch tone, and event links', async () => {
    fetchBucketTrace.mockResolvedValueOnce(traceResponse({
      summary: { ...traceResponse().summary, rebasingAsset: true },
    }));
    const mismatchTarget: InspectedBucket = {
      ...TARGET,
      bucket: {
        ...TARGET.bucket,
        check: { comparedAt: 100, delta: bigNumberify('-5'), derivedBalance: bigNumberify('10'), observedAt: 100, observedBalance: bigNumberify('5') },
        protocol: 'aave-v3',
        status: 'mismatch',
      },
    };

    const wrapper = mountDrawer(mismatchTarget);
    await flushPromises();

    expect(fetchBucketTrace).toHaveBeenCalledWith({ asset: ASSET, limit: 50, location: 'ethereum', locationLabel: ACCOUNT, protocol: 'aave-v3' });
    expect(wrapper.text()).toContain('Aave V3');
    expect(wrapper.find('[data-testid="bucket-trace-rebasing-note"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="bucket-trace-summary"]').html()).toContain('text-rui-error');
    expect(wrapper.findAll('[data-testid="bucket-trace-row-status"]').map(el => el.text())).toStrictEqual([
      'data_issues.reconciliation.trace.row_status.applied',
      'data_issues.reconciliation.trace.row_status.stop',
    ]);
    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links[0].props('to')).toStrictEqual({ name: '/history/events/', query: { addresses: ACCOUNT, asset: ASSET, location: 'ethereum' } });
    expect(links[1].props('to')).toStrictEqual({ name: '/history/events/', query: { asset: ASSET, groupIdentifiers: '0xtx1' } });
  });

  it('should link trace rows by row.eventAsset when a folded event asset differs from the bucket asset', async () => {
    fetchBucketTrace.mockResolvedValueOnce(traceResponse({
      rows: [makeRow(101, { eventAsset: 'MATIC', groupIdentifier: '0xswap1' })],
    }));

    const wrapper = mountDrawer({ ...TARGET, bucket: { ...TARGET.bucket, asset: 'POL' } });
    await flushPromises();

    const rowLink = wrapper.get('[data-testid="bucket-trace-row-link"]').getComponent(RouterLinkStub);
    expect(rowLink.props('to')).toStrictEqual({
      name: '/history/events/',
      query: { asset: 'MATIC', groupIdentifiers: '0xswap1' },
    });
  });

  it('should recover from an initial load failure on retry', async () => {
    fetchBucketTrace.mockRejectedValueOnce(new Error('network down')).mockResolvedValueOnce(traceResponse());
    const wrapper = mountDrawer();
    await flushPromises();

    await wrapper.get('[data-testid="bucket-trace-error"] [data-testid="failure-strip-retry"]').trigger('click');
    await flushPromises();

    expect(fetchBucketTrace).toHaveBeenCalledTimes(2);
    expect(wrapper.findAll('[data-testid="bucket-trace-row"]')).toHaveLength(2);
  });

  it('should keep loaded rows visible when loading more fails and clear the inline error on retry', async () => {
    fetchBucketTrace
      .mockResolvedValueOnce(traceResponse({ pagination: { limit: 50, offset: 0, total: 3, truncated: true } }))
      .mockRejectedValueOnce(new Error('page 2 failed'))
      .mockResolvedValueOnce(traceResponse({ pagination: { limit: 50, offset: 2, total: 3, truncated: false }, rows: [makeRow(103)] }));

    const wrapper = mountDrawer();
    await flushPromises();

    await wrapper.get('[data-testid="bucket-trace-load-more"]').trigger('click');
    await flushPromises();
    expect(wrapper.findAll('[data-testid="bucket-trace-row"]')).toHaveLength(2);
    expect(wrapper.find('[data-testid="bucket-trace-error"]').exists()).toBe(false);

    await wrapper.get('[data-testid="bucket-trace-load-more-error"] [data-testid="failure-strip-retry"]').trigger('click');
    await flushPromises();
    expect(wrapper.find('[data-testid="bucket-trace-load-more-error"]').exists()).toBe(false);
    expect(wrapper.findAll('[data-testid="bucket-trace-row"]')).toHaveLength(3);
    expect(wrapper.find('[data-testid="bucket-trace-load-more"]').exists()).toBe(false);
  });

  it('should prepend earlier events when the initial response starts at a non-zero offset', async () => {
    fetchBucketTrace
      .mockResolvedValueOnce(traceResponse({ pagination: { limit: 50, offset: 20, total: 30, truncated: true }, rows: [makeRow(201), makeRow(202)] }))
      .mockResolvedValueOnce(traceResponse({ pagination: { limit: 20, offset: 0, total: 30, truncated: true }, rows: [makeRow(101)] }));

    const wrapper = mountDrawer();
    await flushPromises();

    await wrapper.get('[data-testid="bucket-trace-load-earlier"]').trigger('click');
    await flushPromises();
    expect(fetchBucketTrace).toHaveBeenLastCalledWith(expect.objectContaining({ limit: 20, offset: 0 }));
    expect(wrapper.find('[data-testid="bucket-trace-load-earlier"]').exists()).toBe(false);
    expect(wrapper.findAll('[data-testid="bucket-trace-row"]')).toHaveLength(3);
    expect(wrapper.find('[data-testid="bucket-trace-load-more"]').exists()).toBe(true);
  });

  it('should drop stale responses when switching targets or closing the drawer', async () => {
    const first = deferred<BucketTraceResponse>();
    const second = deferred<BucketTraceResponse>();
    const third = deferred<BucketTraceResponse>();
    fetchBucketTrace
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise)
      .mockReturnValueOnce(third.promise);

    const wrapper = mountDrawer();
    await wrapper.setProps({ target: { ...TARGET, bucket: { ...TARGET.bucket, asset: 'ETH' } } });
    second.resolve(traceResponse({ rows: [makeRow(999)] }));
    await flushPromises();
    first.resolve(traceResponse({ rows: [makeRow(1), makeRow(2)] }));
    await flushPromises();
    expect(wrapper.findAll('[data-testid="bucket-trace-row"]')).toHaveLength(1);

    await wrapper.setProps({ target: { ...TARGET, bucket: { ...TARGET.bucket, asset: 'USDC' } } });
    await wrapper.setProps({ modelValue: false });
    third.resolve(traceResponse({ rows: [makeRow(3), makeRow(4)] }));
    await flushPromises();
    expect(wrapper.find('[data-testid="bucket-trace-rows"]').exists()).toBe(false);
  });

  it('should ignore request cancellations and wrap ZodError as an unsupported failure', async () => {
    fetchBucketTrace.mockRejectedValueOnce(new RequestCancelledError('aborted'));
    const cancelled = mountDrawer();
    await flushPromises();
    expect(cancelled.find('[data-testid="bucket-trace-error"]').exists()).toBe(false);

    fetchBucketTrace.mockRejectedValueOnce(new ZodError([]));
    const invalid = mountDrawer();
    await flushPromises();
    const strip = invalid.get('[data-testid="bucket-trace-error"]');
    expect(strip.text()).toContain('data_issues.reconciliation.failure.unexpected_response');
    expect(strip.find('[data-testid="failure-strip-retry"]').exists()).toBe(false);
  });
});
