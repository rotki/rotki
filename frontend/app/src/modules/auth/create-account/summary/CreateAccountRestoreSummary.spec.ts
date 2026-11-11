import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import CreateAccountRestoreSummary from '@/modules/auth/create-account/summary/CreateAccountRestoreSummary.vue';
import '@test/i18n';

const ActionsStub = {
  emits: ['back', 'next'],
  name: 'CreateAccountStepActions',
  props: ['nextLabel', 'nextTestId', 'issueCount', 'loading'],
  template: '<div><button data-testid="back" @click="$emit(\'back\')" /><button data-testid="next" @click="$emit(\'next\')" /></div>',
};

function createWrapper(error: string = ''): VueWrapper {
  return mount(CreateAccountRestoreSummary, {
    global: {
      stubs: {
        CreateAccountErrorAlert: { props: ['error'], template: '<div data-testid="error">{{ error }}</div>' },
        CreateAccountStepActions: ActionsStub,
        RuiButton: { emits: ['click'], template: '<button @click="$emit(\'click\')"><slot /></button>' },
      },
    },
    props: {
      apiKey: 'abcdefgh1234',
      error,
      loading: false,
      username: 'restored',
    },
  });
}

describe('createAccountRestoreSummary', () => {
  it('should name the API key by its last four characters only', () => {
    const premium = createWrapper().find('[data-testid=create-account-summary-premium]').text();

    expect(premium).toContain('create_account.summary.premium_value');
    expect(premium).toContain('1234');
    expect(premium).not.toContain('abcdefgh');
  });

  it('should show the profile name', () => {
    expect(createWrapper().find('[data-testid=create-account-summary-profile]').text()).toContain('restored');
  });

  it.each([
    ['create-account-summary-premium', 'premium'],
    ['create-account-summary-profile', 'profile'],
  ])('should send the user back to change %s', async (testId, step) => {
    const wrapper = createWrapper();

    await wrapper.find(`[data-testid=${testId}] button`).trigger('click');

    expect(wrapper.emitted('go-to')?.[0]).toStrictEqual([step]);
  });

  /** A restore keeps the backup's own settings, so the summary asks for none. */
  it('should not offer analytics, which the backup decides', () => {
    expect(createWrapper().find('[data-testid=create-account-usage-analytics]').exists()).toBe(false);
  });

  it('should confirm the restore', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=next]').trigger('click');

    expect(wrapper.emitted('confirm')).toHaveLength(1);
  });

  it('should show the error of a failed restore', () => {
    expect(createWrapper('invalid key').find('[data-testid=error]').text()).toBe('invalid key');
  });
});
