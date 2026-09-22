import type { BankAuthChallenge, BankAuthenticationRequest, BankSetupError } from '@/modules/banks/types';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import BankAuthenticationDialog from '@/modules/banks/components/BankAuthenticationDialog.vue';
import '@test/i18n';

const { answerBankAuthentication, setMessage } = vi.hoisted(() => ({
  answerBankAuthentication: vi.fn(),
  setMessage: vi.fn(),
}));

vi.mock('@/modules/banks/use-banks', () => ({
  useBanks: (): Record<string, unknown> => ({ answerBankAuthentication }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
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

  it('should keep the dialog open and show the reason when the bank refuses the TAN', async () => {
    answerBankAuthentication.mockResolvedValue(err<BankSetupError>({ message: 'The TAN was rejected by the bank', type: 'rejected' }));
    wrapper = createWrapper(request);

    await wrapper.find('[data-testid=bank-auth-response] input').setValue('000000');
    await confirm();

    expect(setMessage).toHaveBeenCalledExactlyOnceWith({
      description: 'The TAN was rejected by the bank',
      title: 'bank_settings.errors.setup_title',
    });
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should close without answering when cancelled', async () => {
    wrapper = createWrapper(request);

    wrapper.findComponent(BigDialogStub).vm.$emit('cancel');
    await flushPromises();

    expect(answerBankAuthentication).not.toHaveBeenCalled();
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
  });
});
