import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { mount } from '@vue/test-utils';
import { set } from '@vueuse/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DataIssueInlineActions from '@/modules/history/data-issues/components/DataIssueInlineActions.vue';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import { createRuiPlugin } from '@/plugins/rui';

const { matchingAllowed } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { matchingAllowed: ref<boolean>(true) };
});

vi.mock('@/modules/premium/use-feature-access', () => ({
  PremiumFeature: { ASSET_MOVEMENT_MATCHING: 'asset_movement_matching' },
  useFeatureAccess: (): { allowed: typeof matchingAllowed } => ({ allowed: matchingAllowed }),
}));

function createIssue(overrides: Partial<DataIssue> = {}): DataIssue {
  return {
    asset: 'ETH',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    eventIdentifier: 42,
    groupIdentifier: 'grp-1',
    id: 1,
    kind: IssueKind.MISSING_PRICE,
    location: 'ethereum',
    locationLabel: null,
    payload: {},
    protocol: null,
    resolvedAt: null,
    severity: IssueSeverity.WARNING,
    state: IssueState.OPEN,
    suggestedActions: [],
    tsEnd: 1710000000000,
    tsStart: 1710000000000,
    ...overrides,
  };
}

describe('dataIssueInlineActions', () => {
  beforeEach(() => {
    set(matchingAllowed, true);
  });

  it('should render price, ignore asset, and ignore event buttons for missing_price and emit on click', async () => {
    const issue = createIssue({ kind: IssueKind.MISSING_PRICE });
    const wrapper = mount(DataIssueInlineActions, {
      global: { plugins: [createRuiPlugin({})] },
      props: { issue },
    });

    expect(wrapper.find('[data-testid="data-issue-inline-set_manual_price"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="data-issue-inline-ignore_asset"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="data-issue-inline-ignore_group"]').exists()).toBe(true);

    await wrapper.find('[data-testid="data-issue-inline-set_manual_price"]').trigger('click');
    expect(wrapper.emitted('action')?.[0]).toStrictEqual([{ action: 'set_manual_price', issue }]);
  });

  it('should render add acquisition, match transfer, and confirm zero basis for missing_cost_basis', async () => {
    const issue = createIssue({ kind: IssueKind.MISSING_COST_BASIS });
    const wrapper = mount(DataIssueInlineActions, {
      global: { plugins: [createRuiPlugin({})] },
      props: { issue },
    });

    await wrapper.find('[data-testid="data-issue-inline-confirm_zero_basis"]').trigger('click');
    expect(wrapper.emitted('action')?.[0]).toStrictEqual([{ action: 'confirm_zero_basis', issue }]);
    expect(wrapper.find('[data-testid="data-issue-inline-add_acquisition"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="data-issue-inline-match_transfer"]').exists()).toBe(true);
  });

  it('should show unignore_asset on incomplete_swap only when reason is ignored_asset', () => {
    const ignoredAssetWrapper = mount(DataIssueInlineActions, {
      global: { plugins: [createRuiPlugin({})] },
      props: {
        issue: createIssue({
          kind: IssueKind.INCOMPLETE_SWAP,
          payload: {
            eventIdentifier: 1,
            eventIdentifiers: [1],
            excludedAssets: ['SPAM'],
            groupIdentifier: 'grp-1',
            missingOrExcludedReason: 'ignored_asset',
            presentLegs: [],
          },
        }),
      },
    });
    expect(ignoredAssetWrapper.find('[data-testid="data-issue-inline-unignore_asset"]').exists()).toBe(true);

    const missingLegWrapper = mount(DataIssueInlineActions, {
      global: { plugins: [createRuiPlugin({})] },
      props: {
        issue: createIssue({
          kind: IssueKind.INCOMPLETE_SWAP,
          payload: {
            eventIdentifier: 1,
            eventIdentifiers: [1],
            excludedAssets: [],
            groupIdentifier: 'grp-1',
            missingOrExcludedReason: 'missing_counterpart_leg',
            presentLegs: [],
          },
        }),
      },
    });
    expect(missingLegWrapper.find('[data-testid="data-issue-inline-unignore_asset"]').exists()).toBe(false);
    expect(missingLegWrapper.find('[data-testid="data-issue-inline-dismiss_as_standalone"]').exists()).toBe(true);
  });

  it('should render auto-match, match transfer, and mark external for unmatched_exchange_transfer', () => {
    const wrapper = mount(DataIssueInlineActions, {
      global: { plugins: [createRuiPlugin({})] },
      props: { issue: createIssue({ kind: IssueKind.UNMATCHED_EXCHANGE_TRANSFER }) },
    });

    expect(wrapper.find('[data-testid="data-issue-inline-auto_match_exchange_transfer"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="data-issue-inline-match_transfer"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="data-issue-inline-resolve_as_external"]').exists()).toBe(true);
  });

  it('should render nothing for terminal issues', () => {
    const wrapper = mount(DataIssueInlineActions, {
      global: { plugins: [createRuiPlugin({})] },
      props: { issue: createIssue({ kind: IssueKind.MISSING_PRICE, state: IssueState.RESOLVED }) },
    });

    expect(wrapper.find('[data-testid="data-issue-inline-actions"]').exists()).toBe(false);
  });

  it('should disable resolve_as_external for non-premium users and emit nothing on click', async () => {
    set(matchingAllowed, false);
    const wrapper = mount(DataIssueInlineActions, {
      global: { plugins: [createRuiPlugin({})] },
      props: { issue: createIssue({ kind: IssueKind.UNMATCHED_EXCHANGE_TRANSFER }) },
    });

    const button = wrapper.get('[data-testid="data-issue-inline-resolve_as_external"]');
    expect(button.attributes('disabled')).toBeDefined();
    await button.trigger('click');
    expect(wrapper.emitted('action')).toBeUndefined();
  });
});
