import type { ActivityId } from '@/modules/task-center/core/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { accountAddActivity, EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
import { addAccountLink } from '@/modules/accounts/add-account-link';
import DockTrackAction from '@/modules/task-center/components/DockTrackAction.vue';

const push = vi.fn<(to: unknown) => Promise<void>>().mockResolvedValue(undefined);
const acknowledge = vi.fn<(id: ActivityId) => void>();
const modelExpanded = ref<boolean>(true);

vi.mock('vue-router', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useRouter: (): { push: typeof push } => ({ push }),
}));

vi.mock('@/modules/task-center/use-task-dock', () => ({
  useTaskDock: (): { acknowledge: typeof acknowledge; modelExpanded: typeof modelExpanded } => ({ acknowledge, modelExpanded }),
}));

function createWrapper(props: { addresses: string[]; dismisses?: ActivityId }): VueWrapper {
  return mount(DockTrackAction, { props });
}

describe('dockTrackAction', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(modelExpanded, true);
  });

  it('should open the add dialog holding the addresses on Ethereum, folding the panel', async () => {
    await createWrapper({ addresses: ['0xa', '0xb'] }).find('[data-testid=dock-track-action]').trigger('click');

    expect(push).toHaveBeenCalledExactlyOnceWith(addAccountLink({ addresses: ['0xa', '0xb'], chain: 'eth' }));
    expect(get(modelExpanded)).toBe(false);
  });

  it('should dismiss the job it answers, and nothing when it answers none', async () => {
    const job = accountAddActivity.id({ chain: EVM_PSEUDO_CHAIN, target: { address: '0xa', kind: 'address' } });
    await createWrapper({ addresses: ['0xa'], dismisses: job }).find('[data-testid=dock-track-action]').trigger('click');
    await createWrapper({ addresses: ['0xb'] }).find('[data-testid=dock-track-action]').trigger('click');

    expect(acknowledge).toHaveBeenCalledExactlyOnceWith(job);
  });
});
