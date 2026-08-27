import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { describe, expect, it, vi } from 'vitest';
import { UNMATCHED_ACTIONS, UNMATCHED_LAYOUTS, type UnmatchedLayout, type UnmatchedRowActionSpec, type UnmatchedRowOptionalAction } from '@/modules/history/events/unmatched-actions';
import UnmatchedActions from '@/modules/history/events/UnmatchedActions.vue';

const labels = {
  findMatch: 'Find match',
  findMatchAnyway: 'Find match anyway',
  ignore: 'Ignore',
  ignoreTooltip: 'Ignore tooltip',
  restore: 'Restore',
  restoreTooltip: 'Restore tooltip',
  showInEventsTooltip: 'Show in events',
};

const markExternal: UnmatchedRowOptionalAction = {
  label: 'Mark external',
  tooltip: 'Mark external tooltip',
};

const createCounterpart: UnmatchedRowOptionalAction = {
  label: 'Create counterpart',
  tooltip: 'Create counterpart tooltip',
};

type Wrapper = VueWrapper<InstanceType<typeof UnmatchedActions>>;

function mountActions(layout: UnmatchedLayout, spec: Partial<UnmatchedRowActionSpec> = {}, ignoreLoading = false): Wrapper {
  return mount(UnmatchedActions, {
    attachTo: document.body,
    props: { ignoreLoading, layout, spec: { labels, ...spec } },
  });
}

function inMenu(testId: string): HTMLElement | null {
  return document.body.querySelector(`[data-testid="${testId}"]`);
}

/**
 * The overflow menu teleports its content to the body, so it is queried there rather than
 * through the wrapper, and it lands a tick after the menu opens.
 */
async function openOverflow(wrapper: Wrapper): Promise<void> {
  wrapper.findComponent({ name: 'RuiMenu' }).vm.$emit('update:modelValue', true);
  await flushPromises();
  await vi.waitFor(() => {
    expect(inMenu('unmatched-action-find-match')).not.toBeNull();
  });
}

describe('modules/history/events/UnmatchedActions', () => {
  describe('card layout', () => {
    it('should keep find-match labelled and the rest of the line as icons', async () => {
      const wrapper = mountActions(UNMATCHED_LAYOUTS.CARD, { markExternal });

      expect(wrapper.find('[data-testid=unmatched-action-primary]').text()).toBe('Find match');
      // the others carry no label at this width, only an accessible name
      expect(wrapper.find('[data-testid=unmatched-action-show-in-events]').attributes('aria-label')).toBe('Show in events');
      expect(wrapper.find('[data-testid=unmatched-action-ignore]').attributes('aria-label')).toBe('Ignore');
      expect(wrapper.find('[data-testid=unmatched-action-mark-external]').attributes('aria-label')).toBe('Mark external');

      await wrapper.find('[data-testid=unmatched-action-primary]').trigger('click');
      await wrapper.find('[data-testid=unmatched-action-show-in-events]').trigger('click');
      await wrapper.find('[data-testid=unmatched-action-ignore]').trigger('click');
      await wrapper.find('[data-testid=unmatched-action-mark-external]').trigger('click');

      expect(wrapper.emitted('action')).toEqual([
        [UNMATCHED_ACTIONS.FIND_MATCH],
        [UNMATCHED_ACTIONS.SHOW_IN_EVENTS],
        [UNMATCHED_ACTIONS.IGNORE],
        [UNMATCHED_ACTIONS.MARK_EXTERNAL],
      ]);
    });

    it('should not raise an overflow when nothing is left for it', () => {
      const wrapper = mountActions(UNMATCHED_LAYOUTS.CARD, { markExternal });

      expect(wrapper.find('[data-testid=unmatched-action-overflow]').exists()).toBe(false);
    });

    it('should promote the emphasized mark-external to the labelled action', async () => {
      const wrapper = mountActions(UNMATCHED_LAYOUTS.CARD, { markExternal: { ...markExternal, emphasize: true } });

      expect(wrapper.find('[data-testid=unmatched-action-primary]').text()).toBe('Mark external');
      // promoted, so it is not repeated as an icon
      expect(wrapper.find('[data-testid=unmatched-action-mark-external]').exists()).toBe(false);

      await wrapper.find('[data-testid=unmatched-action-primary]').trigger('click');

      expect(wrapper.emitted('action')).toEqual([[UNMATCHED_ACTIONS.MARK_EXTERNAL]]);
    });

    it('should promote the emphasized create-counterpart to the labelled action', () => {
      const wrapper = mountActions(UNMATCHED_LAYOUTS.CARD, {
        createCounterpart: { ...createCounterpart, emphasize: true },
        markExternal,
      });

      expect(wrapper.find('[data-testid=unmatched-action-primary]').text()).toBe('Create counterpart');
    });

    it('should keep the demoted find-match and create-counterpart in the overflow', async () => {
      const wrapper = mountActions(UNMATCHED_LAYOUTS.CARD, {
        createCounterpart,
        markExternal: { ...markExternal, emphasize: true },
      });
      await openOverflow(wrapper);

      expect(inMenu('unmatched-action-find-match')?.textContent).toContain('Find match anyway');
      expect(inMenu('unmatched-action-create-counterpart')).not.toBeNull();

      inMenu('unmatched-action-find-match')?.click();
      await flushPromises();

      expect(wrapper.emitted('action')).toEqual([[UNMATCHED_ACTIONS.FIND_MATCH]]);
    });

    it('should offer restore and the history link alone on an ignored row', () => {
      const wrapper = mountActions(UNMATCHED_LAYOUTS.CARD, { markExternal, showRestore: true });

      expect(wrapper.find('[data-testid=unmatched-action-restore]').text()).toBe('Restore');
      expect(wrapper.find('[data-testid=unmatched-action-show-in-events]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=unmatched-action-primary]').exists()).toBe(false);
      expect(wrapper.find('[data-testid=unmatched-action-ignore]').exists()).toBe(false);
      expect(wrapper.find('[data-testid=unmatched-action-mark-external]').exists()).toBe(false);
      expect(wrapper.find('[data-testid=unmatched-action-overflow]').exists()).toBe(false);
    });

    it('should disable find-match when matching is not allowed', () => {
      const wrapper = mountActions(UNMATCHED_LAYOUTS.CARD, { matchDisabled: true });

      expect(wrapper.find('[data-testid=unmatched-action-primary]').attributes('disabled')).toBeDefined();
    });
  });

  describe('row layout', () => {
    it('should label every action it offers', () => {
      const wrapper = mountActions(UNMATCHED_LAYOUTS.ROW);

      expect(wrapper.text()).toContain('Find match');
      expect(wrapper.text()).toContain('Ignore');
      expect(wrapper.text()).not.toContain('Restore');
      expect(wrapper.text()).not.toContain('Mark external');
    });

    it('should show restore instead of the match actions on an ignored row', async () => {
      const wrapper = mountActions(UNMATCHED_LAYOUTS.ROW, { showRestore: true });

      expect(wrapper.text()).toContain('Restore');
      expect(wrapper.text()).not.toContain('Find match');

      await wrapper.find('[data-testid=unmatched-action-restore]').trigger('click');

      expect(wrapper.emitted('action')).toEqual([[UNMATCHED_ACTIONS.RESTORE]]);
    });

    it('should render an optional action only when one is given', async () => {
      expect(mountActions(UNMATCHED_LAYOUTS.ROW).find('[data-testid=unmatched-action-mark-external]').exists()).toBe(false);

      const wrapper = mountActions(UNMATCHED_LAYOUTS.ROW, { markExternal });
      await wrapper.find('[data-testid=unmatched-action-mark-external]').trigger('click');

      expect(wrapper.emitted('action')).toEqual([[UNMATCHED_ACTIONS.MARK_EXTERNAL]]);
    });

    it('should fill an emphasized optional action and outline a plain one', () => {
      function variantOf(wrapper: Wrapper, label: string): unknown {
        return wrapper
          .findAllComponents({ name: 'RuiButton' })
          .find(item => item.text() === label)
          ?.props('variant');
      }

      expect(variantOf(mountActions(UNMATCHED_LAYOUTS.ROW, { markExternal }), 'Mark external')).toBe('outlined');
      expect(variantOf(
        mountActions(UNMATCHED_LAYOUTS.ROW, { markExternal: { ...markExternal, emphasize: true } }),
        'Mark external',
      )).toBe('default');
    });

    it('should disable find-match when matching is not allowed', () => {
      const wrapper = mountActions(UNMATCHED_LAYOUTS.ROW, { matchDisabled: true });

      expect(wrapper.find('[data-testid=unmatched-action-find-match]').attributes('disabled')).toBeDefined();
    });
  });

  describe('in-place confirm', () => {
    const confirms = {
      [UNMATCHED_ACTIONS.IGNORE]: { confirmLabel: 'Ignore', message: 'Ignore this row?' },
    };

    it.each([UNMATCHED_LAYOUTS.CARD, UNMATCHED_LAYOUTS.ROW])('should ask in place before acting in the %s layout', async (layout) => {
      const wrapper = mountActions(layout, { confirms });

      await wrapper.find('[data-testid=unmatched-action-ignore]').trigger('click');

      expect(wrapper.emitted('action')).toBeUndefined();
      expect(wrapper.find('[data-testid=unmatched-confirm-strip]').text()).toContain('Ignore this row?');

      await wrapper.find('[data-testid=unmatched-confirm-accept]').trigger('click');

      expect(wrapper.emitted('action')).toEqual([[UNMATCHED_ACTIONS.IGNORE]]);
    });

    it.each([UNMATCHED_LAYOUTS.CARD, UNMATCHED_LAYOUTS.ROW])('should drop the pending action on cancel in the %s layout', async (layout) => {
      const wrapper = mountActions(layout, { confirms });

      await wrapper.find('[data-testid=unmatched-action-ignore]').trigger('click');
      await wrapper.find('[data-testid=unmatched-confirm-cancel]').trigger('click');

      expect(wrapper.emitted('action')).toBeUndefined();
      expect(wrapper.find('[data-testid=unmatched-action-ignore]').exists()).toBe(true);
    });

    it('should act immediately for an action with no confirm entry', async () => {
      const wrapper = mountActions(UNMATCHED_LAYOUTS.CARD, { confirms, markExternal });

      await wrapper.find('[data-testid=unmatched-action-mark-external]').trigger('click');

      expect(wrapper.emitted('action')).toEqual([[UNMATCHED_ACTIONS.MARK_EXTERNAL]]);
    });
  });

  /**
   * The point of the merge: one spec must reach the same actions whichever layout renders it.
   * A card that quietly drops an action, or a row that offers one the card cannot, fails here
   * rather than in a bug report from whoever only ever opens the dialog.
   */
  describe('parity between layouts', () => {
    const spec: UnmatchedRowActionSpec = {
      createCounterpart,
      labels,
      markExternal: { ...markExternal, emphasize: true },
    };

    async function reachableActions(layout: UnmatchedLayout): Promise<string[]> {
      const wrapper = mountActions(layout, spec);

      for (const button of wrapper.findAll('[data-testid^="unmatched-action-"]')) {
        if (button.attributes('data-testid') === 'unmatched-action-overflow')
          continue;
        await button.trigger('click');
      }

      if (wrapper.find('[data-testid=unmatched-action-overflow]').exists()) {
        await openOverflow(wrapper);
        inMenu('unmatched-action-find-match')?.click();
        inMenu('unmatched-action-create-counterpart')?.click();
        await flushPromises();
      }

      const emitted = wrapper.emitted('action') ?? [];
      wrapper.unmount();
      document.body.innerHTML = '';
      return [...new Set(emitted.map(([action]) => String(action)))].sort();
    }

    it('should reach the same actions from either layout', async () => {
      const card = await reachableActions(UNMATCHED_LAYOUTS.CARD);
      const row = await reachableActions(UNMATCHED_LAYOUTS.ROW);

      expect(card).toEqual(row);
      expect(card).toEqual([
        UNMATCHED_ACTIONS.CREATE_COUNTERPART,
        UNMATCHED_ACTIONS.FIND_MATCH,
        UNMATCHED_ACTIONS.IGNORE,
        UNMATCHED_ACTIONS.MARK_EXTERNAL,
        UNMATCHED_ACTIONS.SHOW_IN_EVENTS,
      ].sort());
    });
  });
});
