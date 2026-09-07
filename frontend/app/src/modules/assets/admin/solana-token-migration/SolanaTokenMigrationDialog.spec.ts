import type { SolanaTokenMigrationData } from '@/modules/assets/admin/solana-token-migration/use-solana-token-migration-dialog';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SolanaTokenMigrationDialog from '@/modules/assets/admin/solana-token-migration/SolanaTokenMigrationDialog.vue';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

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

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage: vi.fn() }),
}));

const TOKEN: SolanaTokenMigrationData = { address: 'So111', decimals: 9, tokenKind: 'spl-token' };

function createWrapper(modelValue: SolanaTokenMigrationData | undefined = TOKEN): VueWrapper {
  return mount(SolanaTokenMigrationDialog, {
    global: {
      stubs: {
        BigDialog: {
          props: ['display', 'loading', 'title', 'action', 'promptOnClose'],
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
});
