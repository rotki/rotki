import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import LoginBackendToggle from './LoginBackendToggle.vue';

interface ToggleProps {
  open?: boolean;
  loading?: boolean;
  color?: 'primary' | 'success';
}

function mountToggle(props: ToggleProps = {}): VueWrapper<InstanceType<typeof LoginBackendToggle>> {
  return mount(LoginBackendToggle, {
    props: { loading: false, open: false, ...props },
  });
}

describe('modules/auth/login/LoginBackendToggle', () => {
  it('should emit toggle when clicked', async () => {
    const wrapper = mountToggle();

    await wrapper.find('button').trigger('click');

    expect(wrapper.emitted('toggle')).toHaveLength(1);
  });

  it('should not emit toggle while loading', async () => {
    const wrapper = mountToggle({ loading: true });

    await wrapper.find('button').trigger('click');

    expect(wrapper.emitted('toggle')).toBeUndefined();
  });

  it('should disable the button while loading', () => {
    const wrapper = mountToggle({ loading: true });

    expect(wrapper.find('button').attributes('disabled')).toBeDefined();
  });
});
