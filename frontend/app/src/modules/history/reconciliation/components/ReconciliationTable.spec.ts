import type { SpamPrediction, SpamPredictionResponse, SpamPredictionToken } from '@/modules/assets/api/use-asset-spam-prediction-api';
import type { useLocations } from '@/modules/core/common/use-locations';
import type { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import type { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import type { ReconciliationAccount, ReconciliationBucket, StatusCounts } from '@/modules/history/reconciliation/schemas';
import type { AccountDetailState } from '@/modules/history/reconciliation/use-bucket-reconciliation-store';
import { bigNumberify, Blockchain } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, defineComponent } from 'vue';
import SpamAssessmentHint from '@/modules/assets/spam/SpamAssessmentHint.vue';
import { beginSession, endSession } from '@/modules/core/session/session-lifecycle';
import ReconciliationTable from '@/modules/history/reconciliation/components/ReconciliationTable.vue';
import { accountKeyOf } from '@/modules/history/reconciliation/use-reconciliation-rows';
import { createRuiPlugin } from '@/plugins/rui';

const { predictSpam } = vi.hoisted(() => ({
  predictSpam: vi.fn<(tokens: SpamPredictionToken[]) => Promise<SpamPredictionResponse>>(),
}));

vi.mock(import('@/modules/assets/api/use-asset-spam-prediction-api'), async importOriginal => ({
  ...await importOriginal(),
  useAssetSpamPredictionApi: (): { predictSpam: typeof predictSpam } => ({ predictSpam }),
}));

vi.mock('@/modules/history/events/mapping/use-history-event-counterparty-mappings', () => ({
  useHistoryEventCounterpartyMappings: (): ReturnType<typeof useHistoryEventCounterpartyMappings> =>
    createMock<ReturnType<typeof useHistoryEventCounterpartyMappings>>({
      getBaseCounterpartyData: () => undefined,
    }),
}));

vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: (): ReturnType<typeof useLocations> => createMock<ReturnType<typeof useLocations>>({
    useLocationData: () => computed(() => undefined),
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): ReturnType<typeof useSupportedChains> => createMock<ReturnType<typeof useSupportedChains>>({
    matchChain: (location: string) => (location === 'ethereum' ? Blockchain.ETH : undefined),
  }),
}));

const RouterLinkStub = defineComponent({
  name: 'RouterLink',
  props: { to: { type: [Object, String], required: true } },
  template: '<a><slot /></a>',
});

function makeCounts(overrides: Partial<StatusCounts> = {}): StatusCounts {
  return {
    blocked: 0,
    mismatch: 0,
    notCompared: 0,
    pending: 1,
    reconciled: 0,
    ...overrides,
  };
}

function makeAccount(index: number): ReconciliationAccount {
  return {
    counts: makeCounts(),
    historySyncedTo: 1_700_000_000,
    isExchange: false,
    lastComparedAt: 1_700_000_000,
    lastEventTs: 1_700_000_000_000,
    location: 'ethereum',
    locationLabel: `0x${index.toString(16).padStart(40, '0')}`,
  };
}

function makeBucket(asset: string): ReconciliationBucket {
  return {
    asset,
    check: null,
    derivedBalance: bigNumberify('10'),
    issueId: null,
    issueKind: null,
    lastEventTs: 1_700_000_000_000,
    observedAt: 1_700_000_000,
    observedBalance: bigNumberify('10'),
    protocol: null,
    reasons: ['observation_superseded'],
    status: 'pending',
    stop: null,
  };
}

describe('reconciliationTable', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    predictSpam.mockReset();
    predictSpam.mockResolvedValue({});
  });

  afterEach(() => {
    endSession();
  });

  it('should render more than 10 account groups without silently clipping rows', () => {
    const accounts = Array.from({ length: 15 }, (_, idx) => makeAccount(idx + 1));
    const wrapper = mount(ReconciliationTable, {
      global: {
        plugins: [createPinia(), createRuiPlugin({})],
        stubs: {
          AssetDetails: true,
          CounterpartyDisplay: true,
          HashLink: true,
          RouterLink: RouterLinkStub,
        },
      },
      props: {
        accounts,
        details: {},
        view: 'all',
      },
    });

    expect(wrapper.findAll('[data-testid="reconciliation-account-row"]')).toHaveLength(15);
  });

  it('should auto-expand matching accounts when filtered and bubble inspect-trace events', async () => {
    const account = makeAccount(1);
    const bucket = makeBucket('eip155:1/erc20:0x6df1');
    const detail: AccountDetailState = {
      buckets: [bucket],
      loaded: true,
      loading: false,
      pagination: { limit: 50, offset: 0, total: 1 },
      statusKey: 'all',
    };

    const wrapper = mount(ReconciliationTable, {
      global: {
        plugins: [createPinia(), createRuiPlugin({})],
        stubs: {
          AssetDetails: true,
          CounterpartyDisplay: true,
          HashLink: true,
          ReconciliationAmount: true,
          RouterLink: RouterLinkStub,
          TimeAgoDisplay: true,
        },
      },
      props: {
        accounts: [account],
        autoExpand: true,
        details: { [accountKeyOf(account)]: detail },
        view: 'all',
      },
    });

    // Forwarded even when `details[key].loaded` is true so `ensureAccount` validates `statusKey`
    expect(wrapper.emitted('expand')?.[0]).toStrictEqual([account]);

    const inspectButton = wrapper.get('[data-testid="reconciliation-inspect-trace"]');
    await inspectButton.trigger('click');

    expect(wrapper.emitted('inspect-trace')?.[0]).toStrictEqual([{ account, bucket }]);
  });

  it('should cap auto-expanded accounts at 20 on broad filters', () => {
    const accounts = Array.from({ length: 25 }, (_, idx) => makeAccount(idx + 1));
    const wrapper = mount(ReconciliationTable, {
      global: {
        plugins: [createPinia(), createRuiPlugin({})],
        stubs: {
          AssetDetails: true,
          CounterpartyDisplay: true,
          HashLink: true,
          RouterLink: RouterLinkStub,
        },
      },
      props: {
        accounts,
        autoExpand: true,
        details: {},
        view: 'all',
      },
    });

    expect(wrapper.emitted('expand')).toHaveLength(20);
  });

  it('should re-emit expand when an already-open account returns after its cached details were cleared', async () => {
    const account = makeAccount(1);
    const detail: AccountDetailState = {
      buckets: [makeBucket('ETH')],
      loaded: true,
      loading: false,
      pagination: { limit: 50, offset: 0, total: 1 },
      statusKey: 'all',
    };
    const wrapper = mount(ReconciliationTable, {
      global: {
        plugins: [createPinia(), createRuiPlugin({})],
        stubs: {
          AssetDetails: true,
          CounterpartyDisplay: true,
          HashLink: true,
          ReconciliationAmount: true,
          RouterLink: RouterLinkStub,
          TimeAgoDisplay: true,
        },
      },
      props: {
        accounts: [account],
        autoExpand: true,
        details: { [accountKeyOf(account)]: detail },
        view: 'all',
      },
    });
    expect(wrapper.emitted('expand')).toHaveLength(1);

    await wrapper.setProps({ accounts: [], autoExpand: true, details: {} });
    await wrapper.setProps({ accounts: [account], autoExpand: false, details: {} });

    expect(wrapper.emitted('expand')).toHaveLength(2);
    expect(wrapper.emitted('expand')?.[1]).toStrictEqual([account]);
  });

  it('should assess expanded ERC-20 buckets and leave native assets without a spam estimate', async () => {
    beginSession();
    const token = 'eip155:1/erc20:0x6df1';
    const prediction: SpamPrediction = {
      flagged: true,
      modelReasons: [],
      observedSignals: [],
      spamProbability: 0.89,
      threshold: 0.5,
    };
    predictSpam.mockResolvedValueOnce({ [token]: prediction });

    const account = makeAccount(1);
    const detail: AccountDetailState = {
      buckets: [makeBucket(token), makeBucket('ETH')],
      loaded: true,
      loading: false,
      pagination: { limit: 50, offset: 0, total: 2 },
      statusKey: 'all',
    };

    const wrapper = mount(ReconciliationTable, {
      global: {
        plugins: [createPinia(), createRuiPlugin({})],
        stubs: {
          AssetDetails: true,
          CounterpartyDisplay: true,
          HashLink: true,
          ReconciliationAmount: true,
          RouterLink: RouterLinkStub,
          SpamAssessmentHint: true,
          TimeAgoDisplay: true,
        },
      },
      props: {
        accounts: [account],
        autoExpand: true,
        details: { [accountKeyOf(account)]: detail },
        view: 'all',
      },
    });
    await flushPromises();

    expect(predictSpam).toHaveBeenCalledExactlyOnceWith([{ identifier: token }]);
    const assessments = wrapper.findAllComponents(SpamAssessmentHint).map(hint => hint.props('assessment'));
    expect(assessments).toContainEqual({ prediction, status: 'ready' });
    expect(assessments).toContain(undefined);
  });
});
