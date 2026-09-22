import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { msg } from '@/message-key';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { type ActivityModel, assembleActivityModel } from './core/model';
import {
  type Activity,
  ActivityKind,
  ActivitySourceType,
  ActivityStatus,
  type ActivityWaiting,
  makeActivityId,
  WaitingReason,
} from './core/types';
import { useWaitingLabel } from './use-waiting-label';

const activities = ref<Activity[]>([]);

const getAddressName = vi.fn<(address: string, blockchain?: string) => string | undefined>();

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): { getAddressName: typeof getAddressName } => ({ getAddressName }),
}));

vi.mock('./use-task-center', () => ({
  useTaskCenter: (): { model: ComputedRef<ActivityModel> } => ({
    model: computed<ActivityModel>(() => assembleActivityModel(get(activities), (key: string): string => key)),
  }),
}));

const ethereum: Activity = {
  cancellable: false,
  id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'eth'),
  kind: ActivityKind.BLOCKCHAIN_BALANCES,
  percentage: -1,
  rerunnable: false,
  source: { type: ActivitySourceType.NATIVE },
  status: ActivityStatus.RUNNING,
  subtitle: { key: msg.$t('task_center.activity.blockchain_balances.chain'), params: { chain: 'Ethereum' } },
  title: 'Blockchain balances',
};

const ADDRESS = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045';

const account: Activity = {
  cancellable: true,
  id: makeActivityId(ActivityKind.TX_SYNC, 'eth', ADDRESS),
  kind: ActivityKind.TX_SYNC,
  percentage: -1,
  rerunnable: false,
  source: { type: ActivitySourceType.NATIVE },
  status: ActivityStatus.RUNNING,
  subtitle: { key: msg.$t('task_center.activity.tx_sync.address'), params: { address: ADDRESS, chain: 'Ethereum' } },
  title: 'Transaction sync',
};

function queued(waiting?: ActivityWaiting): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.PNL_REPORT, 'report'),
    kind: ActivityKind.PNL_REPORT,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status: ActivityStatus.PENDING,
    title: 'Profit and loss report',
    waiting,
  };
}

describe('useWaitingLabel', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(activities, [ethereum, account]);
    getAddressName.mockReset();
  });

  it('should name an account it waits on by its saved or ENS name', () => {
    getAddressName.mockImplementation((address, chain) => (address === ADDRESS && chain === 'eth' ? 'vitalik.eth' : undefined));

    const label = useWaitingLabel().waitingLabel(queued({ on: account.id, reason: WaitingReason.DEPENDENCY }));

    expect(label).toBe('task_dock.waiting.dependency::vitalik.eth');
  });

  it('should name an unnamed account by its truncated address, never the whole one', () => {
    const label = useWaitingLabel().waitingLabel(queued({ on: account.id, reason: WaitingReason.DEPENDENCY }));

    expect(label).toBe(`task_dock.waiting.dependency::${truncateAddress(ADDRESS)}`);
  });

  it('should neither name nor show the account while privacy mode is on', () => {
    getAddressName.mockReturnValue('vitalik.eth');
    useSettingsRepo().updateFrontend({ scrambleData: true, scrambleMultiplier: 7 });

    const label = useWaitingLabel().waitingLabel(queued({ on: account.id, reason: WaitingReason.DEPENDENCY }));

    expect(label).not.toContain('vitalik.eth');
    expect(label).not.toContain(truncateAddress(ADDRESS));
  });

  it('should say nothing for an activity that is not waiting', () => {
    expect(useWaitingLabel().waitingLabel(queued())).toBeUndefined();
  });

  it('should name the dependency by what it acts on', () => {
    const label = useWaitingLabel().waitingLabel(queued({ on: ethereum.id, reason: WaitingReason.DEPENDENCY }));

    expect(label).toBe('task_dock.waiting.dependency::Ethereum');
  });

  it('should name the parent a child waits to start', () => {
    const label = useWaitingLabel().waitingLabel(queued({ on: ethereum.id, reason: WaitingReason.PARENT }));

    expect(label).toBe('task_dock.waiting.parent::Ethereum');
  });

  it('should fall back to other work when what it waits on has left the model', () => {
    const label = useWaitingLabel().waitingLabel(queued({ on: makeActivityId(ActivityKind.TX_SYNC, 'gone'), reason: WaitingReason.DEPENDENCY }));

    expect(label).toBe('task_dock.waiting.other_work');
  });

  it.each([
    [WaitingReason.HISTORY_SYNC, 'task_dock.waiting.history_sync'],
    [WaitingReason.REDECODE, 'task_dock.waiting.redecode'],
    [WaitingReason.MATCHING, 'task_dock.waiting.matching'],
    [WaitingReason.SLOT, 'task_dock.waiting.slot'],
  ])('should explain a %s hold in its own words', (reason, key) => {
    expect(useWaitingLabel().waitingLabel(queued({ reason }))).toBe(key);
  });
});
