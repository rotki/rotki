import type { ManualBalance, RawManualBalance } from '@/modules/balances/types/manual-balances';
import { bigNumberify } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import ManualBalancesDialog from '@/modules/accounts/manual-balances/ManualBalancesDialog.vue';
import { BalanceType } from '@/modules/balances/types/balances';

const { refreshPrice, refreshPrices, saveBalance, setMessage } = vi.hoisted(() => ({
  refreshPrice: vi.fn(async () => {}),
  refreshPrices: vi.fn(async () => {}),
  saveBalance: vi.fn(),
  setMessage: vi.fn(),
}));

vi.mock('@/modules/balances/manual/use-manual-balances', () => ({
  useManualBalances: (): Record<string, Mock> => ({ save: saveBalance }),
}));

vi.mock('@/modules/assets/prices/use-price-refresh', () => ({
  usePriceRefresh: (): Record<string, Mock> => ({ refreshPrice, refreshPrices }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, Mock> => ({ setMessage }),
}));

const validate = vi.fn(() => true);
const savePrice = vi.fn(async () => false);

/**
 * The dialog reaches into the form through a template ref, so the stub has to expose the two
 * methods it calls. An auto-stub would leave the ref pointing at a component with neither.
 */
const FormStub = defineComponent({
  name: 'ManualBalancesForm',
  props: ['modelValue', 'errorMessages', 'stateUpdated', 'submitting'],
  setup(_, { expose }): () => VNode {
    expose({ savePrice, validate });
    return () => h('div');
  },
});

/** `BigDialog` teleports and owns the footer buttons; the two here stand for confirm and cancel. */
const BigDialogStub = {
  emits: ['confirm', 'cancel'],
  name: 'BigDialog',
  props: ['title', 'subtitle', 'display', 'loading', 'action', 'promptOnClose'],
  template: `<div>
    <slot />
    <button data-testid="stub-confirm" @click="$emit('confirm')" />
    <button data-testid="stub-cancel" @click="$emit('cancel')" />
  </div>`,
};

function rawBalance(): RawManualBalance {
  return {
    amount: bigNumberify(10),
    asset: 'ETH',
    balanceType: BalanceType.ASSET,
    label: 'savings',
    location: 'external',
    tags: null,
  };
}

function savedBalance(): ManualBalance {
  return { ...rawBalance(), identifier: 1 };
}

function createWrapper(modelValue: ManualBalance | RawManualBalance): VueWrapper<any> {
  return mount(ManualBalancesDialog, {
    global: {
      stubs: {
        BigDialog: BigDialogStub,
        ManualBalancesForm: FormStub,
      },
    },
    props: { modelValue },
  });
}

async function confirm(wrapper: VueWrapper<any>): Promise<void> {
  await wrapper.find('[data-testid=stub-confirm]').trigger('click');
  await flushPromises();
}

describe('manualBalancesDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    validate.mockReturnValue(true);
    savePrice.mockResolvedValue(false);
    saveBalance.mockResolvedValue({ success: true });
  });

  describe('the heading', () => {
    it('should announce an edit when the balance has been saved before', () => {
      const dialog = createWrapper(savedBalance()).findComponent(BigDialogStub);

      expect(dialog.props('title')).toBe('manual_balances.dialog.edit.title');
      expect(dialog.props('subtitle')).toBe('manual_balances.dialog.edit.subtitle');
    });

    it('should announce an addition when the balance is new', () => {
      const dialog = createWrapper(rawBalance()).findComponent(BigDialogStub);

      expect(dialog.props('title')).toBe('manual_balances.dialog.add.title');
      expect(dialog.props('subtitle')).toBe('');
    });
  });

  describe('saving', () => {
    it('should not save a form that does not validate', async () => {
      validate.mockReturnValue(false);
      const wrapper = createWrapper(rawBalance());

      await confirm(wrapper);

      expect(saveBalance).not.toHaveBeenCalled();
      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
    });

    it('should send the balance and close on success', async () => {
      const wrapper = createWrapper(savedBalance());

      await confirm(wrapper);

      expect(saveBalance).toHaveBeenCalledWith(savedBalance());
      expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([undefined]);
    });

    it('should keep the dialog open when the save fails', async () => {
      saveBalance.mockResolvedValue({ message: 'nope', success: false });
      const wrapper = createWrapper(savedBalance());

      await confirm(wrapper);

      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
    });

    it('should discard the balance when the dialog is dismissed', async () => {
      const wrapper = createWrapper(savedBalance());

      await wrapper.find('[data-testid=stub-cancel]').trigger('click');

      expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([undefined]);
      expect(saveBalance).not.toHaveBeenCalled();
    });
  });

  /**
   * A manual price entered alongside the balance changes the value the list shows, so both the
   * asset's own price and the aggregate are refetched. Nothing was entered means nothing to refetch.
   */
  describe('prices saved with the balance', () => {
    it('should refresh the asset and the aggregate when a price was saved', async () => {
      savePrice.mockResolvedValue(true);

      await confirm(createWrapper(savedBalance()));

      expect(refreshPrice).toHaveBeenCalledWith('ETH');
      expect(refreshPrices).toHaveBeenCalledTimes(1);
    });

    it('should refresh nothing when no price was saved', async () => {
      await confirm(createWrapper(savedBalance()));

      expect(refreshPrice).not.toHaveBeenCalled();
      expect(refreshPrices).not.toHaveBeenCalled();
    });
  });

  /**
   * A balance without an identifier is one the list has never shown, and it lands on the tab its
   * type belongs to rather than the one the user was looking at.
   */
  describe('the tab a new balance lands on', () => {
    it('should switch to the assets tab for a new asset', async () => {
      const wrapper = createWrapper(rawBalance());

      await confirm(wrapper);

      expect(wrapper.emitted('update-tab')?.[0]).toEqual(['assets']);
    });

    it('should switch to the liabilities tab for a new liability', async () => {
      const wrapper = createWrapper({ ...rawBalance(), balanceType: BalanceType.LIABILITY });

      await confirm(wrapper);

      expect(wrapper.emitted('update-tab')?.[0]).toEqual(['liabilities']);
    });

    it('should leave the tab alone when an existing balance is edited', async () => {
      const wrapper = createWrapper(savedBalance());

      await confirm(wrapper);

      expect(wrapper.emitted('update-tab')).toBeUndefined();
    });
  });

  describe('reporting a rejected save', () => {
    it('should mark the offending fields and re-validate the form', async () => {
      const errors = { label: ['already taken'] };
      saveBalance.mockResolvedValue({ message: errors, success: false });
      const wrapper = createWrapper(savedBalance());

      await confirm(wrapper);

      expect(wrapper.findComponent(FormStub).props('errorMessages')).toEqual(errors);
      expect(validate).toHaveBeenCalledTimes(2);
      expect(setMessage).not.toHaveBeenCalled();
    });

    it('should surface a message that names no field', async () => {
      saveBalance.mockResolvedValue({ message: 'the backend said no', success: false });
      const wrapper = createWrapper(savedBalance());

      await confirm(wrapper);

      expect(setMessage).toHaveBeenCalledWith({
        description: 'actions.manual_balances.edit.error.description::the backend said no',
      });
      expect(wrapper.findComponent(FormStub).props('errorMessages')).toEqual({});
    });

    it('should word the message as an addition when the balance is new', async () => {
      saveBalance.mockResolvedValue({ message: 'the backend said no', success: false });

      await confirm(createWrapper(rawBalance()));

      expect(setMessage).toHaveBeenCalledWith({
        description: 'actions.manual_balances.add.error.description::the backend said no',
      });
    });
  });
});
