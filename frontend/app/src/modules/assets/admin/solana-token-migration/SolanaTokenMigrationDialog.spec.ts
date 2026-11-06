import type { SolanaTokenMigrationData } from '@/modules/assets/admin/solana-token-migration/use-solana-token-migration-dialog';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SolanaTokenMigrationDialog from '@/modules/assets/admin/solana-token-migration/SolanaTokenMigrationDialog.vue';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';

const { migrateSolanaToken, removeIdentifier } = vi.hoisted(() => ({
  migrateSolanaToken: vi.fn(async () => Promise.resolve(true)),
  removeIdentifier: vi.fn(),
}));

vi.mock('@/modules/assets/admin/solana-token-migration/solana-token-migration', () => ({
  useSolanaTokenMigrationApi: (): Record<string, unknown> => ({ migrateSolanaToken }),
}));

vi.mock('@/modules/assets/admin/solana-token-migration/use-solana-token-migration-store', () => ({
  useSolanaTokenMigrationStore: (): Record<string, unknown> => ({ removeIdentifier }),
}));

const TARGET = 'solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';

const TOKEN: SolanaTokenMigrationData = { address: 'So111', decimals: 9, tokenKind: 'spl-token' };

function createWrapper(modelValue: SolanaTokenMigrationData | undefined = TOKEN): VueWrapper {
  return mount(SolanaTokenMigrationDialog, {
    global: {
      stubs: {
        BigDialog: {
          props: ['display', 'loading', 'title', 'action', 'promptOnClose', 'failure', 'failureTitle'],
          template: '<div><slot /></div>',
        },
        ExternalLink: true,
        HintMenuIcon: true,
        SolanaTokenMigrationForm: {
          methods: { validate: (): boolean => true },
          template: '<div data-testid="migration-form" />',
        },
      },
    },
    props: { modelValue, oldAsset: 'SOL-OLD' },
  });
}

describe('modules/assets/admin/solana-token-migration/SolanaTokenMigrationDialog.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('should show the dialog while a token is selected', () => {
    expect(createWrapper().findComponent(BigDialog).props('display')).toBe(true);
  });

  it('should render the form while a token is selected', () => {
    expect(createWrapper().find('[data-testid=migration-form]').exists()).toBe(true);
  });

  it('should clear both selections when cancelled, without migrating', async () => {
    const wrapper = createWrapper();

    wrapper.findComponent(BigDialog).vm.$emit('cancel');
    await flushPromises();

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([undefined]);
    expect(wrapper.emitted('update:oldAsset')?.at(-1)).toEqual([undefined]);
    expect(migrateSolanaToken).not.toHaveBeenCalled();
  });

  it('should migrate nothing until the dialog is confirmed', () => {
    createWrapper();

    expect(migrateSolanaToken).not.toHaveBeenCalled();
  });

  it('should ask the caller to refresh once a confirmed migration lands', async () => {
    const wrapper = createWrapper();

    wrapper.findComponent(BigDialog).vm.$emit('confirm');
    await flushPromises();

    expect(migrateSolanaToken).toHaveBeenCalledOnce();
    expect(wrapper.emitted('refresh')).toHaveLength(1);
  });

  describe('a migration that fails', () => {
    async function confirmRejectedWith(error: Error): Promise<VueWrapper> {
      migrateSolanaToken.mockRejectedValueOnce(error);
      const wrapper = createWrapper();
      wrapper.findComponent(BigDialog).vm.$emit('confirm');
      await flushPromises();
      return wrapper;
    }

    it('should name the failure in the dialog and stay open', async () => {
      const error = new Error('the chain is unreachable');
      const wrapper = await confirmRejectedWith(error);

      const dialog = wrapper.findComponent(BigDialog);
      expect(dialog.props('failure')).toBe(error);
      expect(dialog.props('failureTitle')).toBe('asset_management.solana_token_migration.migration_error');
      expect(dialog.props('display')).toBe(true);
      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
    });

    it('should clear the failure when the migration is confirmed again', async () => {
      const wrapper = await confirmRejectedWith(new Error('boom'));
      migrateSolanaToken.mockImplementationOnce(async () => new Promise(() => {}));

      wrapper.findComponent(BigDialog).vm.$emit('confirm');
      await flushPromises();

      expect(wrapper.findComponent(BigDialog).props('failure')).toBeUndefined();
    });
  });

  describe('a migration that collides with an existing asset', () => {
    const collision = new Error(`UNIQUE constraint failed: assets.identifier ${TARGET}`);

    it('should ask about the merge inside the dialog', async () => {
      migrateSolanaToken.mockRejectedValueOnce(collision);
      const wrapper = createWrapper();
      wrapper.findComponent(BigDialog).vm.$emit('confirm');
      await flushPromises();

      const question = wrapper.findComponent(InlineConfirm);
      expect(question.props('message')).toContain('asset_management.solana_token_migration.merge_suggestion.message');
      expect(wrapper.findComponent(BigDialog).props('failure')).toBeUndefined();
      expect(wrapper.emitted('suggest-merge')).toBeUndefined();
    });

    it('should hand the pair to the caller once the merge is accepted', async () => {
      migrateSolanaToken.mockRejectedValueOnce(collision);
      const wrapper = createWrapper();
      wrapper.findComponent(BigDialog).vm.$emit('confirm');
      await flushPromises();

      await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

      expect(wrapper.emitted('suggest-merge')).toEqual([[{ sourceAsset: 'SOL-OLD', targetAsset: TARGET }]]);
      expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([undefined]);
    });

    it('should drop the question and keep the dialog when the merge is declined', async () => {
      migrateSolanaToken.mockRejectedValueOnce(collision);
      const wrapper = createWrapper();
      wrapper.findComponent(BigDialog).vm.$emit('confirm');
      await flushPromises();

      await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');

      expect(wrapper.findComponent(InlineConfirm).exists()).toBe(false);
      expect(wrapper.emitted('suggest-merge')).toBeUndefined();
      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
    });
  });
});
