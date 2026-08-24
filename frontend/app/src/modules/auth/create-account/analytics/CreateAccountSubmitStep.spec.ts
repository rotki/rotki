import type { CreateAccountMode } from '@/modules/auth/create-account/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import CreateAccountErrorAlert from './CreateAccountErrorAlert.vue';
import CreateAccountSubmitAnalytics from './CreateAccountSubmitAnalytics.vue';
import CreateAccountSubmitStep from './CreateAccountSubmitStep.vue';

interface StepProps {
  loading?: boolean;
  mode?: CreateAccountMode;
  error?: string;
  submitUsageAnalytics?: boolean;
}

function mountStep(props: StepProps = {}): VueWrapper<InstanceType<typeof CreateAccountSubmitStep>> {
  return mount(CreateAccountSubmitStep, {
    props: {
      loading: false,
      mode: 'create',
      submitUsageAnalytics: true,
      ...props,
    },
  });
}

describe('modules/auth/create-account/analytics/CreateAccountSubmitStep', () => {
  it('should emit back when the back button is clicked', async () => {
    const wrapper = mountStep();

    await wrapper.findAll('button')[0].trigger('click');

    expect(wrapper.emitted('back')).toHaveLength(1);
    expect(wrapper.emitted('confirm')).toBeUndefined();
  });

  it('should emit confirm when the submit button is clicked', async () => {
    const wrapper = mountStep();

    await wrapper.find('[data-testid=create-account-analytics-continue]').trigger('click');

    expect(wrapper.emitted('confirm')).toHaveLength(1);
    expect(wrapper.emitted('back')).toBeUndefined();
  });

  it('should keep the e2e submit selector on the submit button', () => {
    const wrapper = mountStep();

    expect(wrapper.find('[data-testid=create-account-analytics-continue]').exists()).toBe(true);
  });

  it('should hide the error alert when there is no error', () => {
    const wrapper = mountStep();

    expect(wrapper.findComponent(CreateAccountErrorAlert).exists()).toBe(false);
  });

  it('should show the error alert and forward the message when an error is present', () => {
    const wrapper = mountStep({ error: 'boom' });
    const alert = wrapper.findComponent(CreateAccountErrorAlert);

    expect(alert.exists()).toBe(true);
    expect(alert.props('error')).toBe('boom');
  });

  it('should forward loading to the analytics step and disable both buttons', () => {
    const wrapper = mountStep({ loading: true });

    expect(wrapper.findComponent(CreateAccountSubmitAnalytics).props('loading')).toBe(true);
    const buttons = wrapper.findAll('button');
    expect(buttons[0].attributes('disabled')).toBeDefined();
    expect(buttons[1].attributes('disabled')).toBeDefined();
  });

  it('should propagate the analytics model back to the parent', async () => {
    const wrapper = mountStep({ submitUsageAnalytics: true });

    wrapper.findComponent(CreateAccountSubmitAnalytics).vm.$emit('update:submitUsageAnalytics', false);
    await nextTick();

    expect(wrapper.emitted('update:submitUsageAnalytics')).toEqual([[false]]);
  });
});
