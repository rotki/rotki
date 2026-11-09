import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { ApiRequestError } from '@/modules/core/api/types/errors';
import FailureStrip from './FailureStrip.vue';

describe('failureStrip', () => {
  it('should offer retry when the caller listens for it, and call the listener', async () => {
    const onRetry = vi.fn<() => void>();
    const wrapper = mount(FailureStrip, {
      props: { failure: 'node unreachable', onRetry, title: 'Load failed' },
    });

    await wrapper.find('[data-testid=failure-strip-retry]').trigger('click');

    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('should keep retry for a failure the backend calls transient', () => {
    const wrapper = mount(FailureStrip, {
      props: { failure: new ApiRequestError('down', { failureCause: 'network' }), onRetry: vi.fn<() => void>(), title: 'Load failed' },
    });

    expect(wrapper.find('[data-testid=failure-strip-retry]').exists()).toBe(true);
  });

  it('should offer no retry for a failure no retry can fix, though the caller listens for it', () => {
    const wrapper = mount(FailureStrip, {
      props: { failure: new ApiRequestError('key rejected', { failureCause: 'auth' }), onRetry: vi.fn<() => void>(), title: 'Load failed' },
    });

    expect(wrapper.text()).toContain('key rejected');
    expect(wrapper.find('[data-testid=failure-strip-retry]').exists()).toBe(false);
  });

  it('should offer no retry when nobody listens for it', () => {
    const wrapper = mount(FailureStrip, {
      props: { failure: 'too many devices', title: 'Save failed' },
    });

    expect(wrapper.find('[data-testid=failure-strip-retry]').exists()).toBe(false);
  });

  it('should show the caller\'s action beside the message', () => {
    const wrapper = mount(FailureStrip, {
      props: { failure: 'too many devices', title: 'Save failed' },
      slots: { action: '<button data-testid="extra-action">Learn more</button>' },
    });

    expect(wrapper.find('[data-testid=extra-action]').exists()).toBe(true);
  });
});
