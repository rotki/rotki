import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ActionCenterGroup from '@/modules/core/action-center/ActionCenterGroup.vue';
import { type ActionCenterSection, type ActionItem, type ActionTarget, ActionUrgency } from '@/modules/core/action-center/types';

function createItem(overrides: Partial<ActionItem> = {}): ActionItem {
  const target: ActionTarget = { kind: 'route', to: { name: '/balances/blockchain/' } };
  return {
    actionLabel: 'match',
    checkTarget: target,
    choices: [],
    count: 3,
    description: 'description',
    icon: 'lu-git-compare-arrows',
    id: 'unmatched-bridges',
    informational: false,
    loading: false,
    locked: false,
    minimumTier: null,
    options: [],
    urgency: ActionUrgency.DECISION,
    target,
    title: 'Unmatched bridge transactions',
    ...overrides,
  };
}

function section(items: ActionItem[]): ActionCenterSection {
  return { id: 'history', items, title: 'History' };
}

function mountGroup(props: { items?: ActionItem[]; folded?: boolean; newIds?: string[] } = {}): VueWrapper {
  return mount(ActionCenterGroup, {
    props: {
      folded: props.folded ?? false,
      newIds: props.newIds ?? [],
      section: section(props.items ?? [createItem()]),
    },
  });
}

const toggle = (wrapper: VueWrapper): ReturnType<VueWrapper['find']> => wrapper.find('[data-testid=actions-center-section-toggle]');
const rowCount = (wrapper: VueWrapper): number => wrapper.findAll('[data-testid=actions-center-row]').length;

describe('modules/core/action-center/ActionCenterGroup', () => {
  it('should show its rows under an expanded header', () => {
    const wrapper = mountGroup({ items: [createItem({ id: 'a' }), createItem({ id: 'b' })] });

    expect(rowCount(wrapper)).toBe(2);
    expect(toggle(wrapper).attributes('aria-expanded')).toBe('true');
    expect(wrapper.find('[data-testid=actions-center-section-count]').exists()).toBe(false);
  });

  it('should ask to fold when the header is clicked, and to unfold when folded', async () => {
    const wrapper = mountGroup();
    await toggle(wrapper).trigger('click');

    const folded = mountGroup({ folded: true });
    await toggle(folded).trigger('click');

    expect(wrapper.emitted('update:folded')).toEqual([[true]]);
    expect(folded.emitted('update:folded')).toEqual([[false]]);
  });

  it('should hide its rows when folded, keeping how many there are on the header', () => {
    const wrapper = mountGroup({ folded: true, items: [createItem({ id: 'a' }), createItem({ id: 'b' })] });

    expect(rowCount(wrapper)).toBe(0);
    expect(toggle(wrapper).attributes('aria-expanded')).toBe('false');
    expect(wrapper.find('[data-testid=actions-center-section-count]').text()).toBe('2');
  });

  it('should say on a folded header that a new row is inside', () => {
    const items = [createItem({ id: 'a' }), createItem({ id: 'b' })];

    expect(mountGroup({ folded: true, items, newIds: ['b'] }).find('[data-testid=actions-center-section-new]').exists()).toBe(true);
    expect(mountGroup({ folded: true, items, newIds: [] }).find('[data-testid=actions-center-section-new]').exists()).toBe(false);
  });
});
