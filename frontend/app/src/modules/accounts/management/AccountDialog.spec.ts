import { Blockchain } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, type VNode } from 'vue';
import { type AccountManageState, createNewBlockchainAccount } from '@/modules/accounts/blockchain/use-account-manage';
import AccountDialog from '@/modules/accounts/management/AccountDialog.vue';

const {
  currentTier,
  ethStakedLimit,
  loading,
  modelErrorMessages,
  pending,
  premium,
  resetSaveError,
  save,
  saveError,
  saveErrorIsPremium,
  validate,
  validatorsLimitInfo,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    currentTier: ref<string>('free'),
    ethStakedLimit: ref<number>(0),
    loading: ref<boolean>(false),
    modelErrorMessages: ref<Record<string, string[]>>({}),
    pending: ref<boolean>(false),
    premium: ref<boolean>(false),
    resetSaveError: vi.fn(),
    save: vi.fn<(state: AccountManageState) => Promise<boolean>>(async () => true),
    saveError: ref<string>(''),
    saveErrorIsPremium: ref<boolean>(false),
    validate: vi.fn<() => Promise<boolean>>(async () => true),
    validatorsLimitInfo: ref<{ limit: number; showWarning: boolean; total: number }>({
      limit: 4,
      showWarning: false,
      total: 0,
    }),
  };
});

vi.mock('@/modules/accounts/blockchain/use-account-manage', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/accounts/blockchain/use-account-manage')>(),
  useAccountManage: (): Record<string, unknown> => ({
    modelErrorMessages,
    pending,
    resetSaveError,
    save,
    saveError,
    saveErrorIsPremium,
  }),
}));

vi.mock('@/modules/accounts/use-account-loading', () => ({
  useAccountLoading: (): Record<string, unknown> => ({ loading }),
}));

vi.mock('@/modules/accounts/use-eth-staking', () => ({
  useEthStaking: (): Record<string, unknown> => ({ validatorsLimitInfo }),
}));

vi.mock('@/modules/premium/use-premium-helper', () => ({
  usePremiumHelper: (): Record<string, unknown> => ({ currentTier, ethStakedLimit, premium }),
}));

/** Exposes `validate` under the name the dialog calls on its form ref. */
vi.mock('@/modules/accounts/management/AccountForm.vue', async () => {
  const { defineComponent, h } = await import('vue');
  return {
    __esModule: true,
    default: defineComponent({
      name: 'AccountForm',
      setup(_props, { expose }): () => VNode {
        expose({ validate });
        return () => h('div', { 'data-testid': 'account-form' });
      },
    }),
  };
});

/** Renders the dialog body and surfaces the action bar the spec drives. */
const BigDialogStub = defineComponent({
  emits: ['confirm', 'cancel'],
  props: ['display', 'title', 'subtitle', 'action', 'loading', 'promptOnClose'],
  template: `<div v-if="display">
    <span class="title">{{ title }}</span>
    <span class="subtitle">{{ subtitle }}</span>
    <button data-testid="confirm" :disabled="action.disabled" @click="$emit('confirm')" />
    <button data-testid="cancel" @click="$emit('cancel')" />
    <slot />
  </div>`,
});

function createWrapper(modelValue: AccountManageState | undefined = createNewBlockchainAccount()): VueWrapper<any> {
  return mount(AccountDialog, {
    global: {
      stubs: {
        'BigDialog': BigDialogStub,
        'ExternalLink': true,
        'I18nT': { props: ['keypath'], template: '<span>{{ keypath }}</span>' },
        'i18n-t': { props: ['keypath'], template: '<span>{{ keypath }}</span>' },
        'RuiAlert': { template: '<div><slot /></div>' },
      },
    },
    props: { chainIds: [], modelValue },
  });
}

/** The same account with an address typed into it, which is an edit rather than a new target. */
function edited(): AccountManageState {
  return {
    ...createNewBlockchainAccount(),
    data: [{ address: '0x9531C059098e3d194fF87FebB587aB07B30B1306', tags: null }],
  };
}

function dialog(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent(BigDialogStub);
}

function lastModel(wrapper: VueWrapper<any>): AccountManageState | undefined {
  return wrapper.emitted<[AccountManageState | undefined]>('update:modelValue')?.at(-1)?.[0];
}

async function confirm(wrapper: VueWrapper<any>): Promise<void> {
  await wrapper.find('[data-testid=confirm]').trigger('click');
  await flushPromises();
}

describe('accountDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(currentTier, 'free');
    set(ethStakedLimit, 0);
    set(loading, false);
    set(modelErrorMessages, {});
    set(pending, false);
    set(premium, false);
    set(saveError, '');
    set(saveErrorIsPremium, false);
    set(validatorsLimitInfo, { limit: 4, showWarning: false, total: 0 });
    save.mockResolvedValue(true);
    validate.mockResolvedValue(true);
  });

  describe('the heading', () => {
    it('should say it is adding when the account is new', () => {
      const wrapper = createWrapper();

      expect(dialog(wrapper).props('title')).toBe('blockchain_balances.form_dialog.add_title');
      expect(dialog(wrapper).props('subtitle')).toBe('');
    });

    it('should say it is editing an existing account', () => {
      const wrapper = createWrapper({ chain: Blockchain.ETH2, data: {}, mode: 'edit', type: 'validator' });

      expect(dialog(wrapper).props('title')).toBe('blockchain_balances.form_dialog.edit_title');
      expect(dialog(wrapper).props('subtitle')).toBe('blockchain_balances.form_dialog.edit_subtitle');
    });
  });

  /** Saving an invalid form would send it to the backend to be rejected there instead. */
  describe('confirming', () => {
    it('should save a valid account', async () => {
      const wrapper = createWrapper();

      await confirm(wrapper);

      expect(save).toHaveBeenCalledWith(createNewBlockchainAccount());
    });

    it('should not save while the form rejects it', async () => {
      validate.mockResolvedValue(false);
      const wrapper = createWrapper();

      await confirm(wrapper);

      expect(save).not.toHaveBeenCalled();
    });

    it('should clear the previous errors before trying again', async () => {
      set(modelErrorMessages, { address: ['nope'] });
      const wrapper = createWrapper();

      await confirm(wrapper);

      expect(get(modelErrorMessages)).toEqual({});
      expect(resetSaveError).toHaveBeenCalled();
    });

    it('should close and report a saved account', async () => {
      const wrapper = createWrapper();

      await confirm(wrapper);

      expect(wrapper.emitted('complete')).toHaveLength(1);
      expect(lastModel(wrapper)).toBeUndefined();
    });

    /** A rejected save leaves the dialog open, so the user can correct what the backend refused. */
    it('should stay open when the save is refused', async () => {
      save.mockResolvedValue(false);
      const wrapper = createWrapper();

      await confirm(wrapper);

      expect(wrapper.emitted('complete')).toBeUndefined();
      expect(lastModel(wrapper)).toBeUndefined();
    });
  });

  it('should drop the account and its error on cancel', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=cancel]').trigger('click');

    expect(lastModel(wrapper)).toBeUndefined();
    expect(resetSaveError).toHaveBeenCalled();
  });

  /** The close prompt exists to stop typed-in work being lost, so it follows real edits only. */
  describe('prompting before an unsaved close', () => {
    it('should not prompt on a freshly opened dialog', () => {
      expect(dialog(createWrapper()).props('promptOnClose')).toBe(false);
    });

    it('should prompt once the account has been edited', async () => {
      const wrapper = createWrapper();

      await wrapper.setProps({ modelValue: edited() });

      expect(dialog(wrapper).props('promptOnClose')).toBe(true);
    });

    /**
     * A different chain means the dialog was pointed at another account, not that this one was
     * edited, so there is nothing typed in to lose.
     */
    it('should not prompt when the dialog is pointed at another chain', async () => {
      const wrapper = createWrapper();

      await wrapper.setProps({ modelValue: { ...createNewBlockchainAccount(), chain: Blockchain.BTC } });

      expect(dialog(wrapper).props('promptOnClose')).toBe(false);
    });

    it('should stop prompting once the dialog is closed', async () => {
      const wrapper = createWrapper();
      await wrapper.setProps({ modelValue: edited() });

      await wrapper.setProps({ modelValue: undefined });

      expect(dialog(wrapper).props('promptOnClose')).toBe(false);
    });

    /** A refused save is the one case where nothing changed but the work is still unsaved. */
    it('should prompt after a save the backend refused', async () => {
      save.mockResolvedValue(false);
      const wrapper = createWrapper();

      await confirm(wrapper);

      expect(dialog(wrapper).props('promptOnClose')).toBe(true);
    });
  });

  /** Past the validator limit the account cannot be saved, so the action is closed off. */
  describe('the validator limit', () => {
    it('should refuse to save another validator once it is reached', () => {
      set(validatorsLimitInfo, { limit: 4, showWarning: true, total: 4 });

      const wrapper = createWrapper({ chain: Blockchain.ETH2, data: {}, mode: 'add', type: 'validator' });

      expect(dialog(wrapper).props('action').disabled).toBe(true);
    });

    it('should not stand in the way of editing an existing validator', () => {
      set(validatorsLimitInfo, { limit: 4, showWarning: true, total: 4 });

      const wrapper = createWrapper({ chain: Blockchain.ETH2, data: {}, mode: 'edit', type: 'validator' });

      expect(dialog(wrapper).props('action').disabled).toBe(false);
    });

    it('should not stand in the way of an ordinary account', () => {
      set(validatorsLimitInfo, { limit: 4, showWarning: true, total: 4 });

      const wrapper = createWrapper();

      expect(dialog(wrapper).props('action').disabled).toBe(false);
    });
  });

  describe('reporting a refused save', () => {
    it('should show what the backend said', async () => {
      const wrapper = createWrapper();

      set(saveError, 'the backend said no');
      await nextTick();

      expect(wrapper.text()).toContain('the backend said no');
    });

    /** A premium refusal is explained with an upgrade route rather than the raw message. */
    it('should explain a staking limit rather than repeating the error', async () => {
      set(ethStakedLimit, 4);
      const wrapper = createWrapper();

      set(saveError, 'limit reached');
      set(saveErrorIsPremium, true);
      await nextTick();

      expect(wrapper.text()).toContain('blockchain_balances.eth_staking_limit_error');
      expect(wrapper.text()).not.toContain('limit reached');
    });

    it('should explain having no access at all when there is no limit to name', async () => {
      const wrapper = createWrapper();

      set(saveError, 'no access');
      set(saveErrorIsPremium, true);
      await nextTick();

      expect(wrapper.text()).toContain('blockchain_balances.eth_staking_no_access');
    });
  });

  it('should keep the dialog busy while an account is being saved', () => {
    set(pending, true);

    expect(dialog(createWrapper()).props('loading')).toBe(true);
  });
});
