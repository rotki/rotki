import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import LoginCustomBackendFields from './LoginCustomBackendFields.vue';

interface FieldProps {
  open?: boolean;
  loading?: boolean;
  saved?: boolean;
  errorMessages?: string[];
  url?: string;
  sessionOnly?: boolean;
}

function mountFields(props: FieldProps = {}): VueWrapper<InstanceType<typeof LoginCustomBackendFields>> {
  return mount(LoginCustomBackendFields, {
    props: {
      loading: false,
      open: true,
      saved: false,
      sessionOnly: false,
      url: '',
      ...props,
    },
  });
}

describe('modules/auth/login/LoginCustomBackendFields', () => {
  it('should render nothing while collapsed', () => {
    const wrapper = mountFields({ open: false });

    expect(wrapper.find('input').exists()).toBe(false);
  });

  it('should render the url field while expanded', () => {
    const wrapper = mountFields();

    expect(wrapper.find('input').exists()).toBe(true);
  });

  it('should emit save when the save button is clicked', async () => {
    const wrapper = mountFields({ saved: false, url: 'http://localhost:9001' });

    await wrapper.findAll('button')[0].trigger('click');

    expect(wrapper.emitted('save')).toHaveLength(1);
    expect(wrapper.emitted('clear')).toBeUndefined();
  });

  it('should emit clear instead of save once an override is persisted', async () => {
    const wrapper = mountFields({ saved: true, url: 'http://localhost:9001' });

    await wrapper.findAll('button')[0].trigger('click');

    expect(wrapper.emitted('clear')).toHaveLength(1);
    expect(wrapper.emitted('save')).toBeUndefined();
  });

  it('should propagate url edits to the parent', async () => {
    const wrapper = mountFields();

    await wrapper.find('input').setValue('http://localhost:9001');

    expect(wrapper.emitted('update:url')?.at(-1)).toEqual(['http://localhost:9001']);
  });

  it('should surface validation errors', () => {
    const wrapper = mountFields({ errorMessages: ['not a valid url'] });

    expect(wrapper.text()).toContain('not a valid url');
  });

  it('should disable the url field once the override is persisted', () => {
    const wrapper = mountFields({ saved: true });

    expect(wrapper.find('input').attributes('disabled')).toBeDefined();
  });
});
