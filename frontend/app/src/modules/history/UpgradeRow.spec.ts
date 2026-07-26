import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import UpgradeRow from '@/modules/history/UpgradeRow.vue';

const { usePremiumMock } = vi.hoisted(() => ({ usePremiumMock: vi.fn() }));
vi.mock('@/modules/premium/use-premium', () => ({ usePremium: usePremiumMock }));

/**
 * The global setup stubs `I18nT` with `true`, which drops every slot, so the interpolated content is
 * invisible through the component. This stub renders the slots the messages actually use.
 */
const I18nTStub = {
  props: ['keypath'],
  template: `<div class="message" :data-keypath="keypath">
    <span class="limit"><slot name="limit" /></span>
    <span class="total"><slot name="total" /></span>
    <span class="label"><slot name="label" /></span>
    <span class="from"><slot name="from" /></span>
    <span class="to"><slot name="to" /></span>
  </div>`,
};

const DateDisplayStub = {
  props: ['timestamp'],
  template: `<span class="date">{{ timestamp }}</span>`,
};

describe('upgradeRow', () => {
  let premium: Ref<boolean>;

  function createWrapper(props: Record<string, unknown> = {}): VueWrapper {
    return mount(UpgradeRow, {
      props: { colspan: 5, label: 'events', limit: 10, total: 50, ...props },
      global: { stubs: { DateDisplay: DateDisplayStub, ExternalLink: true, I18nT: I18nTStub } },
    });
  }

  beforeEach(() => {
    premium = ref<boolean>(false);
    usePremiumMock.mockReturnValue(premium);
  });

  it('should use the plain upgrade message when no range is given', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.message').attributes('data-keypath')).toBe('upgrade_row.upgrade');
  });

  it('should use the premium upgrade message for a premium user', () => {
    set(premium, true);
    const wrapper = createWrapper();
    expect(wrapper.find('.message').attributes('data-keypath')).toBe('upgrade_row.upgrade_premium');
  });

  it('should switch to the processed-range message when a range is given', () => {
    const wrapper = createWrapper({ range: { timeEnd: 2000, timeStart: 1000 } });
    expect(wrapper.find('.message').attributes('data-keypath')).toBe('upgrade_row.events');
  });

  it('should use the premium processed-range message for a premium user', () => {
    set(premium, true);
    const wrapper = createWrapper({ range: { timeEnd: 2000, timeStart: 1000 } });
    expect(wrapper.find('.message').attributes('data-keypath')).toBe('upgrade_row.events_premium');
  });

  it('should render the range boundaries as dates', () => {
    const wrapper = createWrapper({ range: { timeEnd: 2000, timeStart: 1000 } });
    expect(wrapper.find('.from .date').text()).toBe('1000');
    expect(wrapper.find('.to .date').text()).toBe('2000');
  });

  it('should omit the date boundaries without a range', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.from .date').exists()).toBe(false);
    expect(wrapper.find('.to .date').exists()).toBe(false);
  });

  it('should render the shown and total counts it was given', () => {
    const wrapper = createWrapper({ limit: 7, total: 42 });
    expect(wrapper.find('.limit').text()).toBe('7');
    expect(wrapper.find('.total').text()).toBe('42');
  });

  it('should span the requested number of columns', () => {
    const wrapper = createWrapper({ colspan: 9 });
    expect(wrapper.find('td').attributes('colspan')).toBe('9');
  });
});
