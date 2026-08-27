import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ActionCenterList from '@/modules/core/action-center/ActionCenterList.vue';
import { type ActionItem, ActionSeverity, type ActionTarget } from '@/modules/core/action-center/types';

function createItem(overrides: Partial<ActionItem> = {}): ActionItem {
  const target: ActionTarget = { kind: 'route', to: { name: '/balances/blockchain/' } };
  return {
    actionLabel: 'match',
    checkTarget: target,
    count: 3,
    description: 'description',
    icon: 'lu-git-compare-arrows',
    id: 'unmatched-bridges',
    informational: false,
    loading: false,
    locked: false,
    minimumTier: null,
    severity: ActionSeverity.WARNING,
    target,
    title: 'Unmatched bridge transactions',
    ...overrides,
  };
}

interface ListProps {
  items: ActionItem[];
  cleared: ActionItem[];
  count: number;
  checking?: boolean;
  refreshing?: boolean;
  checkingHint?: string;
  clearHint?: string;
}

/**
 * Mounts the list with one item and the remaining required props filled in.
 *
 * @remarks
 * The wrapper carries no type argument because a generic SFC has no `InstanceType` to name.
 */
function mountList(props: Partial<ListProps> = {}): VueWrapper {
  return mount(ActionCenterList, {
    props: {
      cleared: [],
      count: 1,
      items: [createItem()],
      ...props,
    },
  });
}

describe('modules/core/action-center/ActionCenterList', () => {
  it('should render a row per item and the cleared ones as a summary', () => {
    const wrapper = mountList({
      cleared: [createItem({ count: 0, id: 'undecoded', title: 'Undecoded transactions' })],
    });

    expect(wrapper.findAll('[data-testid=actions-center-row]')).toHaveLength(1);
    expect(wrapper.find('[data-testid=actions-center-row-count]').text()).toBe('3');
    expect(wrapper.find('[data-testid=actions-center-cleared]').text()).toContain('Undecoded transactions');
  });

  it('should hand the row target up when a row is actioned', async () => {
    const target: ActionTarget = { kind: 'run', run: (): void => {} };
    const wrapper = mountList({ items: [createItem({ target })] });

    await wrapper.find('[data-testid=actions-center-row-action]').trigger('click');

    expect(wrapper.emitted('open')).toEqual([[target]]);
  });

  it('should show a premium gate instead of the action on a locked row', () => {
    const wrapper = mountList({ items: [createItem({ locked: true, minimumTier: 'Basic' })] });

    expect(wrapper.find('[data-testid=actions-center-row-count]').text()).toBe('3');
    expect(wrapper.find('[data-testid=actions-center-row-locked]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=actions-center-row-action]').exists()).toBe(false);
  });

  it('should open a cleared category from its chip, at its own target', async () => {
    const checkTarget: ActionTarget = { kind: 'run', run: (): void => {} };
    const wrapper = mountList({
      cleared: [createItem({ checkTarget, count: 0, id: 'auto-fix-duplicates' })],
      count: 0,
      items: [],
    });

    await wrapper.find('[data-testid=actions-center-cleared-row][data-key="auto-fix-duplicates"]').trigger('click');

    expect(wrapper.emitted('open')).toEqual([[checkTarget]]);
  });

  it('should ask for a re-scan on demand', async () => {
    const wrapper = mountList();

    await wrapper.find('[data-testid=actions-center-rescan]').trigger('click');

    expect(wrapper.emitted('refresh')).toHaveLength(1);
  });

  it('should hide the cleared strip while the counts are still pending', () => {
    const wrapper = mountList({
      checking: true,
      cleared: [createItem({ count: 0, id: 'undecoded' })],
      count: 0,
      items: [],
    });

    expect(wrapper.find('[data-testid=actions-center-cleared]').exists()).toBe(false);
    expect(wrapper.text()).toContain('action_center.title_checking');
  });

  it('should prefer the domain hints over the generic wording', () => {
    const checking = mountList({ checking: true, checkingHint: 'waiting for the sync', count: 0, items: [] });
    const clear = mountList({ clearHint: 'your history is clean', count: 0, items: [] });

    expect(checking.text()).toContain('waiting for the sync');
    expect(checking.text()).not.toContain('action_center.subtitle_checking');
    expect(clear.text()).toContain('your history is clean');
    expect(clear.text()).not.toContain('action_center.subtitle_clear');
  });
});
