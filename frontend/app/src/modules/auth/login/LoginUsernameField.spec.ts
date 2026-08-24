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

// under test the component always renders the plain text field (VITE_TEST is set), so the
// input control is addressed by name rather than by branch.
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

  it('should normalize a cleared value to an empty string', async () => {
    // RuiAutoComplete resets its selection to `undefined` whenever the options change and the
    // current value is not among them, which happens while the profiles are still loading.
    // The parent's model must stay a string.
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
