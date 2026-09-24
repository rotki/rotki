import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { accountAddActivity, EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
import DockSkippedGroup from '@/modules/task-center/components/DockSkippedGroup.vue';
import DockTrackAction from '@/modules/task-center/components/DockTrackAction.vue';
import { type Activity, ActivityKind, ActivitySourceType, ActivityStatus, makeActivityId } from '@/modules/task-center/core/types';

function skipped(id: Activity['id'], kind: ActivityKind): Activity {
  return {
    cancellable: false,
    id,
    kind,
    percentage: 100,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status: ActivityStatus.SKIPPED,
    title: kind,
  };
}

function addition(address: string, chain: string = EVM_PSEUDO_CHAIN): Activity {
  return skipped(accountAddActivity.id({ chain, target: { address, kind: 'address' } }), ActivityKind.ACCOUNTS);
}

function createWrapper(activities: Activity[]): VueWrapper {
  return mount(DockSkippedGroup, {
    props: { activities, reason: 'Already tracked' },
    global: {
      stubs: { HashLink: { props: ['text', 'location'], template: '<i>{{ text }}@{{ location }}</i>' } },
    },
  });
}

describe('dockSkippedGroup', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should show each skipped account as an address link, keeping its chain for the explorer', () => {
    const wrapper = createWrapper([addition('0xaaa', 'optimism'), addition('0xbbb')]);

    expect(wrapper.findAll('[data-testid=dock-skipped-account]').map(link => link.text()))
      .toStrictEqual(['0xaaa@optimism', '0xbbb@']);
    expect(wrapper.find('[data-testid=dock-skipped-names]').exists()).toBe(false);
  });

  it('should link three accounts and count the rest', () => {
    const wrapper = createWrapper(['0xa', '0xb', '0xc', '0xd', '0xe'].map(address => addition(address)));

    expect(wrapper.findAll('[data-testid=dock-skipped-account]')).toHaveLength(3);
    expect(wrapper.find('[data-testid=dock-skipped-accounts]').text()).toContain('task_dock.panel.skipped_more::2');
  });

  it('should offer to track the accounts only when every one of them asked for attention', () => {
    const untracked = (address: string): Activity => ({ ...addition(address), attention: true });
    const track = (activities: Activity[]): VueWrapper<InstanceType<typeof DockTrackAction>> =>
      createWrapper(activities).findComponent(DockTrackAction);

    expect(track([untracked('0xa'), untracked('0xb')]).props('addresses')).toStrictEqual(['0xa', '0xb']);
    expect(track([untracked('0xa'), addition('0xb')]).exists()).toBe(false);
    expect(track([addition('0xa'), addition('0xb')]).exists()).toBe(false);
  });

  it('should fall back to names when any leaf is not an account', () => {
    const chain = skipped(makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'eth'), ActivityKind.BLOCKCHAIN_BALANCES);
    const wrapper = createWrapper([addition('0xaaa'), chain]);

    expect(wrapper.find('[data-testid=dock-skipped-accounts]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=dock-skipped-names]').exists()).toBe(true);
  });
});
