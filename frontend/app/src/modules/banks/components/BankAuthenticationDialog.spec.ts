import type { BankAuthChallenge, BankAuthenticationRequest } from '@/modules/banks/types';
import { flushPromises, mount } from '@vue/test-utils';
import { ok } from 'plainfp/result';
import { describe, expect, it, vi } from 'vitest';
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
  setup: (_props, { slots }) => (): VNode => h('div', slots.default?.()),
});

const request: BankAuthenticationRequest = {
  challenge: {
    challenge: 'Enter TAN',
    challengeData: null,
    challengeHtml: null,
    challengeMimeType: null,
    primitive: 'otp input',
    prompt: 'Enter TAN',
  },
  location: 'fints',
  name: 'Checking',
};

describe('bankAuthenticationDialog', () => {
  it('should answer a connected bank challenge and close after success', async () => {
    answerBankAuthentication.mockResolvedValue(ok(true));
    const wrapper = mount(BankAuthenticationDialog, {
      global: { stubs: { BigDialog: BigDialogStub } },
      props: { modelValue: request },
    });

    await wrapper.find('[data-testid=bank-auth-response] input').setValue('123456');
    wrapper.findComponent(BigDialogStub).vm.$emit('confirm');
    await flushPromises();

    expect(answerBankAuthentication).toHaveBeenCalledWith(request, '123456');
    expect(wrapper.emitted('authenticated')).toEqual([[]]);
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
  });

  it('should replace a decoupled challenge when the bank asks for another poll', async () => {
    const nextChallenge: BankAuthChallenge = {
      ...request.challenge,
      primitive: 'app approval poll',
    };
    answerBankAuthentication.mockResolvedValue(ok(nextChallenge));
    const wrapper = mount(BankAuthenticationDialog, {
      global: { stubs: { BigDialog: BigDialogStub } },
      props: { modelValue: { ...request, challenge: nextChallenge } },
    });

    wrapper.findComponent(BigDialogStub).vm.$emit('confirm');
    await flushPromises();

    expect(answerBankAuthentication).toHaveBeenCalledWith(
      { ...request, challenge: nextChallenge },
      undefined,
    );
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([{
      ...request,
      challenge: nextChallenge,
    }]);
  });
});
