import type { SpamAssessment } from './use-spam-assessments';
import type { SpamPrediction } from '@/modules/assets/api/use-asset-spam-prediction-api';
import { mockT } from '@test/i18n';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import SpamAssessmentHint from './SpamAssessmentHint.vue';

const prediction: SpamPrediction = {
  flagged: true,
  modelReasons: [{
    feature: 'log_transfer_count',
    probabilityDelta: 0.12,
    value: 4,
  }],
  observedSignals: [{ code: 'url', field: 'name' }, { code: 'promotion', field: 'symbol' }],
  spamProbability: 0.9,
  threshold: 0.5,
};

function mountHint(assessment?: SpamAssessment): VueWrapper<InstanceType<typeof SpamAssessmentHint>> {
  return mount(SpamAssessmentHint, {
    global: {
      stubs: {
        RuiChip: { props: ['color'], template: '<span data-testid="spam-chip" :data-color="color"><slot /></span>' },
        RuiIcon: { props: ['name'], template: '<svg :data-icon="name" />' },
        RuiTooltip: { template: '<div><slot name="activator" /><div data-testid="tooltip"><slot /></div></div>' },
      },
    },
    props: { assessment },
  });
}

function ready(overrides: Partial<SpamPrediction> = {}): SpamAssessment {
  return { prediction: { ...prediction, ...overrides }, status: 'ready' };
}

describe('spamAssessmentHint', () => {
  it('should show a high estimate when the backend flags the token', () => {
    const wrapper = mountHint(ready({ spamProbability: 0.5, threshold: 0.5 }));

    expect(wrapper.get('[data-testid=spam-state]').text()).toBe(mockT('spam_estimate.high'));
    expect(wrapper.get('[data-testid=spam-chip]').attributes('data-color')).toBe('warning');
    expect(wrapper.get('[data-testid=spam-score]').text()).toBe(mockT('spam_estimate.score', { percentage: 50 }));
    expect(wrapper.get('[data-testid=spam-advisory]').text()).toBe(mockT('spam_estimate.advisory'));
  });

  it('should follow the backend flag rather than comparing the score to the threshold', () => {
    const wrapper = mountHint(ready({ flagged: false, spamProbability: 0.9, threshold: 0.5 }));

    expect(wrapper.get('[data-testid=spam-state]').text()).toBe(mockT('spam_estimate.low'));
    expect(wrapper.get('[data-testid=spam-chip]').attributes('data-color')).toBe('secondary');
    expect(wrapper.get('[data-testid=spam-score]').text()).toBe(mockT('spam_estimate.score', { percentage: 90 }));
  });

  it('should explain token traits with distinct icons instead of model jargon', () => {
    const wrapper = mountHint(ready());

    const signals = wrapper.get('[data-testid=spam-signals]');
    expect(signals.text()).toContain(mockT('spam_estimate.traits.link', { source: mockT('spam_estimate.traits.name') }));
    expect(signals.text()).toContain(mockT('spam_estimate.traits.promotion', { source: mockT('spam_estimate.traits.symbol') }));
    expect(signals.findAll('svg').map(icon => icon.attributes('data-icon'))).toEqual(['lu-link', 'lu-megaphone']);
    expect(wrapper.get('[data-testid=tooltip]').text()).not.toContain('log transfer count');
  });

  it('should show the transfer count carried by the signal', () => {
    const wrapper = mountHint(ready({ observedSignals: [{ code: 'max_token_transfers', field: 'context', value: 299 }] }));

    expect(wrapper.get('[data-testid=spam-signals]').text()).toBe(mockT('spam_estimate.traits.max_transfers', { count: 299 }));
  });

  it('should describe missing origin data without presenting it as proof of spam', () => {
    const wrapper = mountHint(ready({ observedSignals: [{ code: 'known_origin_unavailable', field: 'context' }] }));

    expect(wrapper.get('[data-testid=spam-signals]').text()).toBe(mockT('spam_estimate.traits.origin'));
  });

  it('should explain when no token details are available', () => {
    const wrapper = mountHint(ready({ observedSignals: [] }));

    expect(wrapper.get('[data-testid=tooltip]').text()).toContain(mockT('spam_estimate.no_signals'));
    expect(wrapper.find('[data-testid=spam-signals]').exists()).toBe(false);
  });

  it.each([
    { color: 'secondary', label: 'spam_estimate.unsupported', status: 'unsupported' },
    { color: 'error', label: 'spam_estimate.unavailable', status: 'unavailable' },
    { color: 'secondary', label: 'spam_estimate.checking', status: 'loading' },
  ] as const)('should state a $status estimate without a score', ({ color, label, status }) => {
    const wrapper = mountHint({ status });

    expect(wrapper.get('[data-testid=spam-state]').text()).toBe(mockT(label));
    expect(wrapper.get('[data-testid=spam-chip]').attributes('data-color')).toBe(color);
    expect(wrapper.find('[data-testid=spam-score]').exists()).toBe(false);
  });

  it('should render nothing for an asset without an assessment', () => {
    const wrapper = mountHint();

    expect(wrapper.find('[data-testid=spam-chip]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=tooltip]').exists()).toBe(false);
  });
});
