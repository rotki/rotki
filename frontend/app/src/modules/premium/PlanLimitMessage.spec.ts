import { externalLinks } from '@shared/external-links';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PlanLimitMessage from '@/modules/premium/PlanLimitMessage.vue';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

const { currentTier, premium } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { currentTier: ref<string>('Free'), premium: ref<boolean>(false) };
});

vi.mock('@/modules/premium/use-premium', () => ({ usePremium: (): typeof premium => premium }));
vi.mock('@/modules/premium/use-premium-helper', () => ({
  usePremiumHelper: (): Record<string, unknown> => ({ currentTier }),
}));

/**
 * The global setup stubs `I18nT` with `true`, which drops every slot, so the interpolated content is
 * invisible through the component. This stub renders the slots the messages actually use.
 */
const I18nTStub = {
  props: ['keypath'],
  template: `<div class="message" :data-keypath="keypath">
    <span class="plan"><slot name="plan" /></span>
    <span class="hidden-count"><slot name="hidden" /></span>
    <span class="total"><slot name="total" /></span>
    <span class="limit"><slot name="limit" /></span>
    <span class="label"><slot name="label" /></span>
    <span class="link"><slot name="link" /></span>
    <span class="from"><slot name="from" /></span>
    <span class="to"><slot name="to" /></span>
  </div>`,
};

const DateDisplayStub = {
  props: ['timestamp'],
  template: `<span class="date">{{ timestamp }}</span>`,
};

const ExternalLinkStub = {
  props: ['text', 'url'],
  template: `<a class="upgrade" :data-url="url">{{ text }}</a>`,
};

function createWrapper(props: Record<string, unknown> = {}): VueWrapper {
  return mount(PlanLimitMessage, {
    props: { label: 'events', limit: 1000, total: 13481, ...props },
    global: { stubs: { DateDisplay: DateDisplayStub, ExternalLink: ExternalLinkStub, I18nT: I18nTStub } },
  });
}

describe('modules/premium/PlanLimitMessage', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useSettingsRepo().updateFrontend({ decimalSeparator: '.', thousandSeparator: ',' });
    set(currentTier, 'Free');
    set(premium, false);
  });

  it('should say how many entries the limit hides when there are more than the limit', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.message').attributes('data-keypath')).toBe('plan_limit.hidden');
    expect(wrapper.find('.hidden-count').text()).toBe('12,481');
    expect(wrapper.find('.total').text()).toBe('13,481');
  });

  it('should group the counts with the user\'s thousand separator', () => {
    useSettingsRepo().updateFrontend({ decimalSeparator: ',', thousandSeparator: '.' });
    const wrapper = createWrapper();
    expect(wrapper.find('.hidden-count').text()).toBe('12.481');
  });

  it('should say the limit is reached when nothing is hidden yet', () => {
    const wrapper = createWrapper({ limit: 10, total: 10 });
    expect(wrapper.find('.message').attributes('data-keypath')).toBe('plan_limit.reached');
  });

  it('should say the limit is reached when it blocks adding, even with entries hidden', () => {
    const wrapper = createWrapper({ adding: true, limit: 4, total: 6 });
    expect(wrapper.find('.message').attributes('data-keypath')).toBe('plan_limit.reached');
  });

  it('should explain the unprocessed part of a report when a range is given', () => {
    const wrapper = createWrapper({ range: { timeEnd: 2000, timeStart: 1000 } });
    expect(wrapper.find('.message').attributes('data-keypath')).toBe('plan_limit.unprocessed');
    expect(wrapper.find('.from .date').text()).toBe('1000');
    expect(wrapper.find('.to .date').text()).toBe('2000');
  });

  it('should keep the report wording when a range is given and the counts agree', () => {
    const wrapper = createWrapper({ limit: 10, range: { timeEnd: 2000, timeStart: 1000 }, total: 10 });
    expect(wrapper.find('.message').attributes('data-keypath')).toBe('plan_limit.unprocessed');
  });

  it('should omit the date boundaries without a range', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.from .date').exists()).toBe(false);
    expect(wrapper.find('.to .date').exists()).toBe(false);
  });

  it('should name the plan the user is on', () => {
    set(currentTier, 'Basic');
    const wrapper = createWrapper();
    expect(wrapper.find('.plan').text()).toBe('Basic');
  });

  it('should send a free user to the premium page', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.upgrade').attributes('data-url')).toBeUndefined();
    expect(wrapper.find('.upgrade').text()).toBe('plan_limit.upgrade');
  });

  it('should send a subscriber to subscription management', () => {
    set(premium, true);
    const wrapper = createWrapper();
    expect(wrapper.find('.upgrade').attributes('data-url')).toBe(externalLinks.manageSubscriptions);
  });
});
