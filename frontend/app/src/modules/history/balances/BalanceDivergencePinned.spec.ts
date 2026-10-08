import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { createMock } from '@test/utils/create-mock';
import { mount } from '@vue/test-utils';
import { get } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { PinnedNames } from '@/modules/session/types';
import BalanceDivergencePinned from './BalanceDivergencePinned.vue';

function mountPanel(props = {}): ReturnType<typeof mount> {
  return mount(BalanceDivergencePinned, {
    global: {
      stubs: {
        AssetDetails: { props: ['asset'], template: '<span>{{ asset }}</span>' },
        BalanceDivergenceView: { template: '<div data-testid="test-divergence-selection" />' },
        DataIssueBalanceDivergence: {
          name: 'DataIssueBalanceDivergence',
          props: ['issue'],
          template: '<div data-testid="test-pinned-diagnostic" />',
        },
        HistoryEventAccount: { props: ['location', 'locationLabel'], template: '<span>{{ locationLabel }}</span>' },
        LocationDisplay: { props: ['identifier'], template: '<span>{{ identifier }}</span>' },
        RuiButton: { emits: ['click'], template: '<button @click="$emit(\'click\')"><slot /></button>' },
        RuiIcon: true,
      },
    },
    props,
  });
}

function makeIssue(): DataIssue {
  return createMock<DataIssue>({
    asset: 'ETH',
    id: 1,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
  });
}

describe('balanceDivergencePinned investigation continuity', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should show the issue search instead of the manual search form', () => {
    const issue = makeIssue();
    const wrapper = mountPanel({ issue });

    expect(wrapper.findComponent({ name: 'DataIssueBalanceDivergence' }).props('issue')).toBe(issue);
    expect(wrapper.find('[data-testid="test-divergence-selection"]').exists()).toBe(false);
  });

  it('should name the account and asset the issue search is about', () => {
    const wrapper = mountPanel({ issue: makeIssue() });

    expect(wrapper.get('[data-testid="balance-divergence-pinned-account"]').text())
      .toBe('0x0000000000000000000000000000000000000001');
    expect(wrapper.get('[data-testid="balance-divergence-pinned-asset"]').text()).toBe('ETH');
  });

  it('should switch to the manual search form when a new search is requested', async () => {
    const { pinnedPanels } = storeToRefs(useAreaVisibilityStore());
    const wrapper = mountPanel({ issue: makeIssue() });

    await wrapper.get('[data-testid="balance-divergence-new-search"]').trigger('click');

    expect(get(pinnedPanels)).toEqual([{ name: PinnedNames.BALANCE_DIVERGENCE, props: {} }]);
  });

  it('should keep the standalone search available when pinned without an issue', () => {
    const wrapper = mountPanel();
    expect(wrapper.find('[data-testid="test-divergence-selection"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="test-pinned-diagnostic"]').exists()).toBe(false);
  });
});
