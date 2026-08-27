import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import LoginUsernameField from './LoginUsernameField.vue';

const savedUsernames = ref<string[]>([]);
const loadProfiles = vi.fn();

vi.mock('@/modules/auth/use-saved-profiles', () => ({
  useSavedProfiles: (): { loadProfiles: () => void; savedUsernames: typeof savedUsernames } => ({
    loadProfiles,
    savedUsernames,
  }),
}));

interface FieldProps {
  modelValue?: string;
  search?: string;
  disabled?: boolean;
  loading?: boolean;
  isDocker?: boolean;
}

/**
 * Mounts the field with every required prop filled in, so a case only names what it varies.
 *
 * @remarks
 * `VITE_TEST` is set, so the component always takes its plain text-field branch and the input can
 * be addressed by component name.
 */
function mountField(props: FieldProps = {}): VueWrapper<InstanceType<typeof LoginUsernameField>> {
  return mount(LoginUsernameField, {
    props: { disabled: false, loading: false, modelValue: '', search: '', ...props },
  });
}

describe('modules/auth/login/LoginUsernameField', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(savedUsernames, ['alice', 'bob']);
  });

  it('should normalize to an empty string the `undefined` the control clears to when still-loading profiles drop the current value', async () => {
    const wrapper = mountField({ modelValue: 'alice' });

    wrapper.findComponent({ name: 'RuiTextField' }).vm.$emit('update:modelValue', undefined);
    await nextTick();

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['']);
  });

  it('should render an undefined model value as an empty string', () => {
    const wrapper = mountField({ modelValue: undefined });

    expect(wrapper.findComponent({ name: 'RuiTextField' }).props('modelValue')).toBe('');
  });

  it('should pass a set value through to the input', () => {
    const wrapper = mountField({ modelValue: 'alice' });

    expect(wrapper.findComponent({ name: 'RuiTextField' }).props('modelValue')).toBe('alice');
  });
});
