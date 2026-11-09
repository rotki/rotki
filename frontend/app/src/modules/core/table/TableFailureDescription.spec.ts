import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { ApiRequestError } from '@/modules/core/api/types/errors';
import TableFailureDescription from './TableFailureDescription.vue';

function createWrapper(failure: unknown): VueWrapper<InstanceType<typeof TableFailureDescription>> {
  return mount(TableFailureDescription, {
    global: { stubs: { RuiButton: { template: '<button v-bind="$attrs"><slot /></button>' }, RuiIcon: true } },
    props: { failure, message: 'the reason' },
  });
}

describe('tableFailureDescription', () => {
  it('should show the reason and offer a retry that emits, for a transient failure', async () => {
    const wrapper = createWrapper(new ApiRequestError('down', { failureCause: 'network' }));

    await wrapper.find('[data-testid=table-failure-retry]').trigger('click');

    expect(wrapper.find('[data-testid=table-failure-message]').text()).toBe('the reason');
    expect(wrapper.emitted('retry')).toHaveLength(1);
  });

  it('should offer a retry for a failure that names no cause', () => {
    expect(createWrapper('the reason').find('[data-testid=table-failure-retry]').exists()).toBe(true);
  });

  it('should show the reason without a retry for a failure no retry can fix', () => {
    const wrapper = createWrapper(new ApiRequestError('no premium', { failureCause: 'forbidden' }));

    expect(wrapper.find('[data-testid=table-failure-message]').text()).toBe('the reason');
    expect(wrapper.find('[data-testid=table-failure-retry]').exists()).toBe(false);
  });
});
