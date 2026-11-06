import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import FailureStrip from './FailureStrip.vue';

describe('failureStrip', () => {
  it('should show the caller\'s action beside the message, keeping retry', async () => {
    const wrapper = mount(FailureStrip, {
      props: { failure: 'too many devices', title: 'Save failed' },
      slots: { action: '<button data-testid="extra-action">Learn more</button>' },
    });

    expect(wrapper.find('[data-testid=extra-action]').exists()).toBe(true);
    await wrapper.find('[data-testid=failure-strip-retry]').trigger('click');
    expect(wrapper.emitted('retry')).toHaveLength(1);
  });

  it('should render no action when the caller passes none', () => {
    const wrapper = mount(FailureStrip, {
      props: { failure: 'too many devices', retryable: false, title: 'Save failed' },
    });

    expect(wrapper.find('[data-testid=failure-strip]').findAll('button')).toHaveLength(0);
  });
});
