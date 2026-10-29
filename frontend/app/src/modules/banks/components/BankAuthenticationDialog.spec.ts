import type { BankAuthChallenge, BankAuthenticationRequest, BankSetupError } from '@/modules/banks/types';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import BankAuthenticationDialog from '@/modules/banks/components/BankAuthenticationDialog.vue';
import '@test/i18n';

const { answerBankAuthentication, syncBanks } = vi.hoisted(() => ({
  answerBankAuthentication: vi.fn(),
  syncBanks: vi.fn<(payload?: { location?: string; name?: string }) => Promise<boolean>>(),
}));

vi.mock('@/modules/banks/use-banks', () => ({
  useBanks: (): Record<string, unknown> => ({ answerBankAuthentication, syncBanks }),
}));

const BigDialogStub = defineComponent({
  emits: ['cancel', 'confirm'],
  props: { action: { default: undefined, type: Object } },
  setup: (_props, { slots }) => (): VNode => h('div', slots.default?.()),
});

const otp: BankAuthChallenge = {
  challenge: 'Enter TAN',
  challengeData: null,
  challengeHtml: null,
  challengeMimeType: null,
  primitive: 'otp input',
  prompt: 'Enter TAN',
};

const request: BankAuthenticationRequest = { challenge: otp, identifier: 'c1', location: 'custom:ing', name: 'Checking' };

describe('bankAuthenticationDialog', () => {
  let wrapper: VueWrapper<InstanceType<typeof BankAuthenticationDialog>>;

  function createWrapper(modelValue: BankAuthenticationRequest): VueWrapper<InstanceType<typeof BankAuthenticationDialog>> {
    return mount(BankAuthenticationDialog, {
      global: { stubs: { BigDialog: BigDialogStub } },
      props: { modelValue },
    });
  }

  function action(): Record<string, unknown> | undefined {
    return wrapper.findComponent(BigDialogStub).props('action');
  }

  async function confirm(): Promise<void> {
    wrapper.findComponent(BigDialogStub).vm.$emit('confirm');
    await flushPromises();
  }

  beforeEach(() => {
    vi.clearAllMocks();
    syncBanks.mockResolvedValue(true);
  });

  it('should answer with the connection identifier only and close after success', async () => {
    answerBankAuthentication.mockResolvedValue(ok(true));
    wrapper = createWrapper(request);

    await wrapper.find('[data-testid=bank-auth-response] input').setValue(' 123456 ');
    await confirm();

    expect(answerBankAuthentication).toHaveBeenCalledExactlyOnceWith({ identifier: 'c1' }, '123456');
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
  });

  it('should keep Continue disabled and send nothing until a TAN is typed', async () => {
    wrapper = createWrapper(request);

    expect(action()).toEqual({ disabled: true, primary: 'bank_settings.authentication.continue' });
    await confirm();
    expect(answerBankAuthentication).not.toHaveBeenCalled();

    await wrapper.find('[data-testid=bank-auth-response] input').setValue('123456');
    expect(action()?.disabled).toBe(false);
  });

  it('should let an app approval be checked without a TAN and show the next poll', async () => {
    const poll: BankAuthChallenge = { ...otp, primitive: 'app approval poll' };
    answerBankAuthentication.mockResolvedValue(ok(poll));
    wrapper = createWrapper({ ...request, challenge: poll });

    expect(action()?.disabled).toBe(false);
    await confirm();

    expect(answerBankAuthentication).toHaveBeenCalledExactlyOnceWith({ identifier: 'c1' }, undefined);
    expect(wrapper.emitted('update:modelValue')).toEqual([[{ ...request, challenge: poll }]]);
  });

  describe('when the bank refuses the answer', () => {
    const refused = err<BankSetupError>({ message: 'The TAN was rejected by the bank', type: 'rejected' });
    const expired = err<BankSetupError>({ message: 'The TAN was rejected by the bank', type: 'expired' });

    it('should show the reason in the dialog and keep the TAN field for another try', async () => {
      answerBankAuthentication.mockResolvedValue(refused);
      wrapper = createWrapper(request);

      await wrapper.find('[data-testid=bank-auth-response] input').setValue('000000');
      await confirm();

      expect(wrapper.find('[data-testid=bank-auth-error]').text()).toBe('The TAN was rejected by the bank');
      expect(wrapper.find('[data-testid=bank-auth-response]').exists()).toBe(true);
      expect(wrapper.emitted('update:modelValue')).toBeUndefined();

      await wrapper.find('[data-testid=bank-auth-response] input').setValue('1');
      expect(wrapper.find('[data-testid=bank-auth-error]').exists()).toBe(false);
    });

    it('should clear the reason of a refused app approval once the next check gets through', async () => {
      const poll: BankAuthChallenge = { ...otp, primitive: 'app approval poll' };
      answerBankAuthentication.mockResolvedValueOnce(refused).mockResolvedValueOnce(ok(poll));
      wrapper = createWrapper({ ...request, challenge: poll });

      await confirm();
      expect(wrapper.find('[data-testid=bank-auth-error]').exists()).toBe(true);

      await confirm();
      expect(wrapper.find('[data-testid=bank-auth-error]').exists()).toBe(false);
    });

    it('should offer a new sync instead of the TAN field once the bank dropped the challenge', async () => {
      answerBankAuthentication.mockResolvedValue(expired);
      wrapper = createWrapper(request);

      await wrapper.find('[data-testid=bank-auth-response] input').setValue('000000');
      await confirm();

      expect(wrapper.find('[data-testid=bank-auth-error]').text())
        .toBe('bank_settings.authentication.expired::The TAN was rejected by the bank');
      expect(wrapper.find('[data-testid=bank-auth-response]').exists()).toBe(false);
      expect(action()).toEqual({ disabled: false, primary: 'bank_settings.authentication.sync_again' });

      await confirm();

      expect(syncBanks).toHaveBeenCalledExactlyOnceWith({ identifier: 'c1' });
      expect(answerBankAuthentication).toHaveBeenCalledOnce();
      expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
    });
  });

  it('should close without answering when cancelled', async () => {
    wrapper = createWrapper(request);

    wrapper.findComponent(BigDialogStub).vm.$emit('cancel');
    await flushPromises();

    expect(answerBankAuthentication).not.toHaveBeenCalled();
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
  });
});
