import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import CreateAccountStepActions from '@/modules/auth/create-account/CreateAccountStepActions.vue';
import '@test/i18n';

function createWrapper(props: Record<string, unknown> = {}): VueWrapper {
  return mount(CreateAccountStepActions, {
    global: {
      stubs: {
        RuiButton: {
          emits: ['click'],
          props: ['disabled', 'loading'],
          template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
        },
      },
    },
    props: { nextLabel: 'Continue', nextTestId: 'step-next', ...props },
  });
}

describe('createAccountStepActions', () => {
  it('should hand both buttons to the step', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=create-account-back]').trigger('click');
    await wrapper.find('[data-testid=step-next]').trigger('click');

    expect(wrapper.emitted('back')).toHaveLength(1);
    expect(wrapper.emitted('next')).toHaveLength(1);
  });

  it('should keep the primary button enabled, so a press can explain what is missing', () => {
    expect(createWrapper({ issueCount: 3 }).find('[data-testid=step-next]').attributes('disabled')).toBeUndefined();
  });

  it('should disable both buttons while the profile is being created', () => {
    const wrapper = createWrapper({ loading: true });

    expect(wrapper.find('[data-testid=create-account-back]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid=step-next]').attributes('disabled')).toBeDefined();
  });

  it('should count the fields that need attention', () => {
    expect(createWrapper({ issueCount: 2 }).find('[data-testid=create-account-issue-count]').text())
      .toContain('create_account.issue_count');
  });

  it('should say nothing when no field needs attention', () => {
    expect(createWrapper().find('[data-testid=create-account-issue-count]').exists()).toBe(false);
  });
});
