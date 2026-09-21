import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ActionCenterList from '@/modules/core/action-center/ActionCenterList.vue';
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

/** One section holding the given rows, for the cases that are not about grouping. */
function history(items: ActionItem[]): ActionCenterSection[] {
  return [{ id: 'history', items, title: 'History' }];
}

interface ListProps {
  sections: ActionCenterSection[];
  cleared: ActionItem[];
  count: number;
  checking?: boolean;
  refreshing?: boolean;
}

/**
 * Mounts the list with one row and the remaining required props filled in.
 *
 * @remarks
 * The wrapper carries no type argument because a generic SFC has no `InstanceType` to name.
 */
function mountList(props: Partial<ListProps> = {}): VueWrapper {
  return mount(ActionCenterList, {
    props: {
      cleared: [],
      count: 1,
      sections: history([createItem()]),
      ...props,
    },
  });
}

describe('modules/core/action-center/ActionCenterList', () => {
  it('should render a row per item', () => {
    const wrapper = mountList();

    expect(wrapper.findAll('[data-testid=actions-center-row]')).toHaveLength(1);
    expect(wrapper.find('[data-testid=actions-center-row-count]').text()).toBe('3');
  });

  describe('the checked categories', () => {
    const cleared = [createItem({ count: 0, id: 'undecoded', title: 'Undecoded transactions' })];

    it('should fold them into a count next to rows that need attention, and list them on demand', async () => {
      const wrapper = mountList({ cleared });

      expect(wrapper.find('[data-testid=actions-center-cleared-toggle]').attributes('aria-expanded')).toBe('false');
      expect(wrapper.find('[data-testid=actions-center-cleared-row]').exists()).toBe(false);

      await wrapper.find('[data-testid=actions-center-cleared-toggle]').trigger('click');

      expect(wrapper.find('[data-testid=actions-center-cleared-row]').text()).toBe('Undecoded transactions');
    });

    it('should list them when nothing needs attention, since they are the evidence of an all clear', async () => {
      const wrapper = mountList({ cleared, count: 0, sections: [] });

      expect(wrapper.find('[data-testid=actions-center-cleared-row]').text()).toBe('Undecoded transactions');

      await wrapper.find('[data-testid=actions-center-cleared-toggle]').trigger('click');

      expect(wrapper.find('[data-testid=actions-center-cleared-row]').exists()).toBe(false);
    });
  });

  it('should hand the row target up when a row is actioned', async () => {
    const target: ActionTarget = { kind: 'run', run: (): void => {} };
    const wrapper = mountList({ sections: history([createItem({ target })]) });

    await wrapper.find('[data-testid=actions-center-row-action]').trigger('click');

    expect(wrapper.emitted('open')).toEqual([[target]]);
  });

  it('should show a premium gate instead of the action on a locked row', () => {
    const wrapper = mountList({ sections: history([createItem({ locked: true, minimumTier: 'Basic' })]) });

    expect(wrapper.find('[data-testid=actions-center-row-count]').text()).toBe('3');
    expect(wrapper.find('[data-testid=actions-center-row-locked]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=actions-center-row-action]').exists()).toBe(false);
  });

  it('should open a cleared category from its chip, at its own target', async () => {
    const checkTarget: ActionTarget = { kind: 'run', run: (): void => {} };
    const wrapper = mountList({
      cleared: [createItem({ checkTarget, count: 0, id: 'auto-fix-duplicates' })],
      count: 0,
      sections: [],
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
      sections: [],
    });

    expect(wrapper.find('[data-testid=actions-center-cleared]').exists()).toBe(false);
    expect(wrapper.text()).toContain('action_center.title_checking');
  });

  it('should group rows under their section headings, in the order the sections come', () => {
    const wrapper = mountList({
      sections: [
        { id: 'history', items: [createItem({ id: 'undecoded' })], title: 'History' },
        {
          id: 'chains',
          items: [createItem({ id: 'no-available-indexers-base' }), createItem({ id: 'no-available-indexers-gnosis' })],
          title: 'Chains & nodes',
        },
      ],
    });

    const sections = wrapper.findAll('[data-testid=actions-center-section]');
    expect(sections.map(section => section.attributes('data-key'))).toEqual(['history', 'chains']);
    expect(sections[1].text()).toContain('Chains & nodes');
    expect(sections[1].findAll('[data-testid=actions-center-row]')).toHaveLength(2);
  });

  it('should hand a row option target up as an open', async () => {
    const guide: ActionTarget = { kind: 'external', url: 'https://docs.rotki.com' };
    const item = createItem({ options: [{ icon: 'lu-book-open', id: 'guide', label: 'Guide', target: guide }] });
    const wrapper = mountList({ sections: [{ id: 'integrations', items: [item], title: 'Integrations' }] });

    await wrapper.find('[data-testid=actions-center-row-option]').trigger('click');

    expect(wrapper.emitted('open')).toEqual([[guide]]);
  });
});
