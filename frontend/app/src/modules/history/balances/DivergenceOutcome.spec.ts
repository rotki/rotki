import type { HistoricalBalanceDivergenceResponse } from '@/modules/history/balances/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import DivergenceOutcome from '@/modules/history/balances/DivergenceOutcome.vue';

const stubs = {
  RuiAlert: { props: ['type', 'title'], template: '<div :data-type="type" :data-title="title"><slot /></div>' },
};

function createWrapper(
  status: HistoricalBalanceDivergenceResponse['status'],
  text: { summary?: string; nextStep?: string } = { summary: 'summary' },
): VueWrapper {
  return mount(DivergenceOutcome, { global: { stubs }, props: { status, ...text } });
}

describe('divergenceOutcome', () => {
  it.each([
    ['no_divergence', 'success'],
    ['no_checkpoints', 'warning'],
    ['diverged_from_start', 'warning'],
    ['diverged', 'warning'],
  ] as const)('should show a %s result as a %s status named after its outcome', (status, type) => {
    const outcome = createWrapper(status).get('[data-testid=divergence-outcome]');

    expect(outcome.attributes('data-type')).toBe(type);
    expect(outcome.attributes('data-title')).toBe(`balance_divergence.status.${status}`);
  });

  it('should show the summary followed by the next step', () => {
    const wrapper = createWrapper('no_divergence', { nextStep: 'next', summary: 'summary' });

    expect(wrapper.get('[data-testid=divergence-outcome-summary]').text()).toBe('summary');
    expect(wrapper.get('[data-testid=divergence-outcome-next-step]').text()).toBe('next');
  });

  it('should render nothing when there is no text to show', () => {
    expect(createWrapper('diverged', {}).find('[data-testid=divergence-outcome]').exists()).toBe(false);
  });
});
