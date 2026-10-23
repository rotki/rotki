import type { BankAuthChallenge, BankFormData, BankManifest, BankSetupError } from '@/modules/banks/types';
import type { useBanks } from '@/modules/banks/use-banks';
import { createMock } from '@test/utils/create-mock';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import BankConnectionFormDialog from '@/modules/banks/components/BankConnectionFormDialog.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import '@test/i18n';

const { answerBankAuthentication, cancelBankSetup, setupBank, validate } = vi.hoisted(() => ({
  answerBankAuthentication: vi.fn(),
  cancelBankSetup: vi.fn<ReturnType<typeof useBanks>['cancelBankSetup']>(),
  setupBank: vi.fn<ReturnType<typeof useBanks>['setupBank']>(),
  validate: vi.fn(),
}));

vi.mock('@/modules/banks/use-banks', () => ({
  useBanks: (): Record<string, unknown> => ({ answerBankAuthentication, cancelBankSetup, setupBank }),
}));

const otp: BankAuthChallenge = {
  challenge: 'Enter TAN',
  challengeData: null,
  challengeHtml: null,
  challengeMimeType: null,
  primitive: 'otp input',
  prompt: 'Enter TAN',
};

vi.mock('@/modules/banks/components/BankConnectionForm.vue', () => ({
  default: defineComponent({
    props: { errorMessages: { default: (): Record<string, string[]> => ({}), type: Object } },
    setup(props, { expose }) {
      expose({ validate });
      return (): VNode => h('div', { 'data-testid': 'form-stub' }, JSON.stringify(props.errorMessages));
    },
  }),
}));

const BigDialogStub = defineComponent({
  emits: ['cancel', 'confirm'],
  props: { action: { default: undefined, type: Object } },
  setup: (_props, { slots }) => (): VNode => h('div', slots.default?.()),
});

function createForm(): BankFormData {
  return {
    credentials: { api_key: 'login', api_secret: 'secret' },
    location: 'qonto',
    mode: 'add',
    name: 'Qonto main',
    newName: '',
  };
}

describe('bankConnectionFormDialog', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof BankConnectionFormDialog>>;

  function createWrapper(modelValue: BankFormData | undefined): VueWrapper<InstanceType<typeof BankConnectionFormDialog>> {
    return mount(BankConnectionFormDialog, {
      global: {
        plugins: [pinia],
        stubs: { BigDialog: BigDialogStub, Teleport: true },
      },
      props: { modelValue },
    });
  }

  async function confirm(): Promise<void> {
    wrapper.findComponent(BigDialogStub).vm.$emit('confirm');
    await flushPromises();
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();
    validate.mockReturnValue(true);
    cancelBankSetup.mockResolvedValue(undefined);
  });

  it('should save the entry and emit added with the connection identity', async () => {
    setupBank.mockResolvedValue(ok({ historyStartTs: null, success: true }));
    wrapper = createWrapper(createForm());
    await confirm();
    expect(setupBank).toHaveBeenCalledWith(createForm());
    expect(wrapper.emitted('added')).toEqual([[{ location: 'qonto', name: 'Qonto main' }]]);
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
  });

  describe('when closed', () => {
    async function cancel(): Promise<void> {
      wrapper.findComponent(BigDialogStub).vm.$emit('cancel');
      await flushPromises();
    }

    it('should drop a setup waiting on its TAN, so the next add of the name starts clean', async () => {
      setupBank.mockResolvedValue(ok(otp));
      wrapper = createWrapper(createForm());
      await confirm();

      await cancel();

      expect(cancelBankSetup).toHaveBeenCalledExactlyOnceWith({ location: 'qonto', name: 'Qonto main' });
      expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
    });

    it('should leave the backend alone when no setup was started', async () => {
      wrapper = createWrapper(createForm());

      await cancel();

      expect(cancelBankSetup).not.toHaveBeenCalled();
      expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
    });
  });

  it('should not save when the form does not validate', async () => {
    validate.mockReturnValue(false);
    wrapper = createWrapper(createForm());
    await confirm();
    expect(setupBank).not.toHaveBeenCalled();
  });

  it('should map a credential slot error onto its credentials field and leave other fields as they are', async () => {
    setupBank.mockResolvedValue(err<BankSetupError>({ errors: { api_secret: ['wrong'], name: ['taken'] }, type: 'fields' }));
    wrapper = createWrapper(createForm());
    await confirm();
    expect(wrapper.find('[data-testid=bank-setup-error]').exists()).toBe(false);
    expect(JSON.parse(wrapper.find('[data-testid=form-stub]').text())).toEqual({ 'credentials.api_secret': ['wrong'], 'name': ['taken'] });
    expect(wrapper.emitted('added')).toBeUndefined();
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should keep the dialog open and show the reason in it when the bank rejects the request', async () => {
    setupBank.mockResolvedValue(err<BankSetupError>({ message: 'Qonto rejected the credentials', type: 'rejected' }));
    wrapper = createWrapper(createForm());
    await confirm();
    expect(wrapper.find('[data-testid=bank-setup-error]').text()).toBe('bank_settings.errors.setup_message::Qonto, Qonto rejected the credentials');
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();

    setupBank.mockResolvedValue(ok({ historyStartTs: null, success: true }));
    await confirm();
    expect(wrapper.find('[data-testid=bank-setup-error]').exists()).toBe(false);
  });

  it('should keep the dialog open without an error when the backend requests authentication', async () => {
    setupBank.mockResolvedValue(ok(otp));
    wrapper = createWrapper(createForm());
    await confirm();
    expect(wrapper.find('[data-testid=bank-setup-error]').exists()).toBe(false);
    expect(wrapper.emitted('added')).toBeUndefined();
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should keep the setup TAN field with the reason when the answer can be sent again', async () => {
    setupBank.mockResolvedValue(ok(otp));
    answerBankAuthentication.mockResolvedValue(err<BankSetupError>({ message: 'Could not connect to the FinTS endpoint', type: 'rejected' }));
    wrapper = createWrapper(createForm());

    await confirm();
    await wrapper.find('[data-testid=bank-auth-response] input').setValue('123456');
    await confirm();

    expect(wrapper.find('[data-testid=bank-setup-error]').text()).toContain('Could not connect to the FinTS endpoint');
    expect(wrapper.find('[data-testid=bank-auth-challenge]').exists()).toBe(true);

    await confirm();
    expect(answerBankAuthentication).toHaveBeenCalledTimes(2);
    expect(setupBank).toHaveBeenCalledOnce();
  });

  it('should go back to the credentials with the reason when the bank dropped the setup TAN', async () => {
    setupBank.mockResolvedValue(ok(otp));
    answerBankAuthentication.mockResolvedValue(err<BankSetupError>({ message: 'The TAN was rejected by the bank', type: 'expired' }));
    wrapper = createWrapper(createForm());

    await confirm();
    await wrapper.find('[data-testid=bank-auth-response] input').setValue('000000');
    await confirm();

    expect(wrapper.find('[data-testid=bank-setup-error]').text()).toContain('The TAN was rejected by the bank');
    expect(wrapper.find('[data-testid=bank-auth-challenge]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=form-stub]').exists()).toBe(true);

    await confirm();
    expect(setupBank).toHaveBeenCalledTimes(2);
  });

  it('should name the bank by its display name once its manifest is loaded', async () => {
    useBankConnectionsStore().setManifests([createMock<BankManifest>({ displayName: 'Qonto Business', location: 'qonto' })]);
    setupBank.mockResolvedValue(err<BankSetupError>({ message: 'Qonto rejected the credentials', type: 'rejected' }));
    wrapper = createWrapper(createForm());
    await confirm();
    expect(wrapper.find('[data-testid=bank-setup-error]').text()).toBe('bank_settings.errors.setup_message::Qonto Business, Qonto rejected the credentials');
  });

  it('should display and answer a TAN challenge without restarting setup', async () => {
    setupBank.mockResolvedValue(ok({
      challenge: 'Enter TAN',
      challengeData: null,
      challengeHtml: null,
      challengeMimeType: null,
      primitive: 'otp input',
      prompt: 'Enter TAN',
    }));
    answerBankAuthentication.mockResolvedValue(ok({ historyStartTs: null, success: true }));
    wrapper = createWrapper(createForm());

    await confirm();
    expect(wrapper.find('[data-testid=bank-auth-challenge]').text()).toContain('Enter TAN');
    await wrapper.find('[data-testid=bank-auth-response] input').setValue('123456');
    await confirm();

    expect(setupBank).toHaveBeenCalledOnce();
    expect(answerBankAuthentication).toHaveBeenCalledWith(
      { location: 'qonto', name: 'Qonto main' },
      '123456',
    );
    expect(wrapper.emitted('added')).toEqual([[{ location: 'qonto', name: 'Qonto main' }]]);
  });

  it('should switch Save to Continue for a TAN and not answer until one is typed', async () => {
    setupBank.mockResolvedValue(ok({
      challenge: 'Enter TAN',
      challengeData: null,
      challengeHtml: null,
      challengeMimeType: null,
      primitive: 'otp input',
      prompt: 'Enter TAN',
    }));
    wrapper = createWrapper(createForm());
    const action = (): Record<string, unknown> | undefined => wrapper.findComponent(BigDialogStub).props('action');

    expect(action()).toEqual({ primary: 'common.actions.save' });
    await confirm();
    expect(action()).toEqual({ disabled: true, primary: 'bank_settings.authentication.continue' });

    await confirm();
    expect(answerBankAuthentication).not.toHaveBeenCalled();
    expect(validate).toHaveBeenCalledOnce();
  });

  it('should discard a pending challenge when the dialog is cancelled', async () => {
    setupBank.mockResolvedValue(ok({
      challenge: 'Enter TAN',
      challengeData: null,
      challengeHtml: null,
      challengeMimeType: null,
      primitive: 'otp input',
      prompt: 'Enter TAN',
    }));
    wrapper = createWrapper(createForm());

    await confirm();
    wrapper.findComponent(BigDialogStub).vm.$emit('cancel');
    await wrapper.setProps({ modelValue: undefined });
    await wrapper.setProps({ modelValue: { ...createForm(), name: 'Another bank' } });

    expect(wrapper.find('[data-testid=bank-auth-challenge]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=form-stub]').exists()).toBe(true);
  });
});
