import type { SpamPrediction } from '@/modules/assets/api/use-asset-spam-prediction-api';
import { mockT } from '@test/i18n';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import NewlyDetectedTokenSpamHint from './NewlyDetectedTokenSpamHint.vue';

const prediction: SpamPrediction = {
  flagged: true,
  modelReasons: [{
    feature: 'log_transfer_count',
    probabilityDelta: 0.12,
    value: 4,
  }],
  observedSignals: ['name: contains URL-like text', 'symbol: contains promotional wording'],
  spamProbability: 0.9,
  threshold: 0.5,
};

function mountHint(props: {
  prediction?: SpamPrediction | null;
  unavailable?: boolean;
}): VueWrapper<InstanceType<typeof NewlyDetectedTokenSpamHint>> {
  return mount(NewlyDetectedTokenSpamHint, {
    global: {
      stubs: {
        RuiIcon: { props: ['name'], template: '<svg :data-icon="name" />' },
        RuiTooltip: { template: '<div><slot name="activator" /><div data-testid="tooltip"><slot /></div></div>' },
      },
    },
    props,
  });
}

describe('newlyDetectedTokenSpamHint', () => {
  it('should show a high estimate at the returned threshold', () => {
    const wrapper = mountHint({
      prediction: { ...prediction, spamProbability: 0.5, threshold: 0.5 },
    });

    expect(wrapper.get('[data-testid=spam-state]').text()).toBe(mockT('asset_table.newly_detected.spam.high'));
    expect(wrapper.get('[data-testid=spam-score]').text()).toBe(
      mockT('asset_table.newly_detected.spam.score', { percentage: 50 }),
    );
    expect(wrapper.get('[data-testid=spam-advisory]').text()).toBe(mockT('asset_table.newly_detected.spam.advisory'));
  });

  it('should show a low estimate below the returned threshold', () => {
    const wrapper = mountHint({
      prediction: { ...prediction, flagged: false, spamProbability: 0.2 },
    });

    expect(wrapper.get('[data-testid=spam-state]').text()).toBe(mockT('asset_table.newly_detected.spam.low'));
    expect(wrapper.get('[data-testid=spam-score]').text()).toBe(
      mockT('asset_table.newly_detected.spam.score', { percentage: 20 }),
    );
    expect(wrapper.get('[data-testid=spam-advisory]').text()).toBe(mockT('asset_table.newly_detected.spam.advisory'));
  });

  it('should explain token traits with distinct icons instead of model jargon', () => {
    const wrapper = mountHint({ prediction });

    const signals = wrapper.get('[data-testid=spam-signals]');
    expect(signals.text()).toContain(mockT('asset_table.newly_detected.spam.traits.link', {
      source: mockT('asset_table.newly_detected.spam.traits.name'),
    }));
    expect(signals.text()).toContain(mockT('asset_table.newly_detected.spam.traits.promotion', {
      source: mockT('asset_table.newly_detected.spam.traits.symbol'),
    }));
    expect(signals.findAll('svg').map(icon => icon.attributes('data-icon'))).toEqual(['lu-link', 'lu-megaphone']);
    expect(wrapper.get('[data-testid=tooltip]').text()).not.toContain('log transfer count');
  });

  it('should describe missing origin data without presenting it as proof of spam', () => {
    const wrapper = mountHint({
      prediction: { ...prediction, observedSignals: ['context: known-origin fraction is unavailable'] },
    });

    expect(wrapper.get('[data-testid=spam-signals]').text()).toBe(mockT('asset_table.newly_detected.spam.traits.origin'));
  });

  it('should retain unfamiliar signals with an information icon', () => {
    const wrapper = mountHint({
      prediction: { ...prediction, observedSignals: ['A newly supported detail'] },
    });

    expect(wrapper.get('[data-testid=spam-signals]').text()).toBe('A newly supported detail');
    expect(wrapper.get('[data-testid=spam-signals] svg').attributes('data-icon')).toBe('lu-info');
  });

  it('should explain when no token details are available', () => {
    const wrapper = mountHint({
      prediction: { ...prediction, observedSignals: [] },
    });

    expect(wrapper.get('[data-testid=tooltip]').text()).toContain(mockT('asset_table.newly_detected.spam.no_signals'));
    expect(wrapper.find('[data-testid=spam-signals]').exists()).toBe(false);
  });

  it('should state an unsupported token without a score', () => {
    const wrapper = mountHint({ prediction: null });

    expect(wrapper.get('[data-testid=spam-state]').text()).toBe(mockT('asset_table.newly_detected.spam.unsupported'));
    expect(wrapper.find('[data-testid=spam-score]').exists()).toBe(false);
  });

  it('should state an unavailable estimate without a score', () => {
    const wrapper = mountHint({ unavailable: true });

    expect(wrapper.get('[data-testid=spam-state]').text()).toBe(mockT('asset_table.newly_detected.spam.unavailable'));
    expect(wrapper.find('[data-testid=spam-score]').exists()).toBe(false);
  });

  it('should state a pending estimate without a score', () => {
    const wrapper = mountHint({});

    expect(wrapper.get('[data-testid=spam-state]').text()).toBe(mockT('asset_table.newly_detected.spam.checking'));
    expect(wrapper.find('[data-testid=spam-score]').exists()).toBe(false);
  });
});
