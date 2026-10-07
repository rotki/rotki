import type { HistoricalBalanceDivergenceResponse } from '@/modules/history/balances/types';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { createMock } from '@test/utils/create-mock';
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import BalanceDivergencePinned from './BalanceDivergencePinned.vue';

function mountPanel(props = {}): ReturnType<typeof mount> {
  return mount(BalanceDivergencePinned, {
    global: {
      stubs: {
        BalanceDivergenceView: { template: '<div data-testid="test-divergence-selection" />' },
        DataIssueBalanceDivergence: {
          name: 'DataIssueBalanceDivergence',
          props: ['issue', 'initialResult'],
          template: '<div data-testid="test-pinned-diagnostic">{{ initialResult.firstDiverged.eventIdentifier }}</div>',
        },
      },
    },
    props,
  });
}

describe('balanceDivergencePinned investigation continuity', () => {
  it('should show the completed issue search without requesting a new search', () => {
    const issue = createMock<DataIssue>({ id: 1 });
    const result = createMock<HistoricalBalanceDivergenceResponse>({
      firstDiverged: createMock<NonNullable<HistoricalBalanceDivergenceResponse['firstDiverged']>>({ eventIdentifier: 123 }),
    });
    const wrapper = mountPanel({ issue, result });

    expect(wrapper.get('[data-testid="test-pinned-diagnostic"]').text()).toBe('123');
    const diagnostic = wrapper.findComponent({ name: 'DataIssueBalanceDivergence' });
    expect(diagnostic.props('issue')).toBe(issue);
    expect(diagnostic.props('initialResult')).toBe(result);
    expect(wrapper.find('[data-testid="test-divergence-selection"]').exists()).toBe(false);
  });

  it('should keep the standalone search available when pinned without an issue', () => {
    const wrapper = mountPanel();
    expect(wrapper.find('[data-testid="test-divergence-selection"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="test-pinned-diagnostic"]').exists()).toBe(false);
  });
});
