import type { HistoryEventCategoryDetailWithId } from '@/modules/history/events/event-type';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import HistoryEventTypeCombination from '@/modules/history/events/HistoryEventTypeCombination.vue';

function createType(overrides: Partial<HistoryEventCategoryDetailWithId> = {}): HistoryEventCategoryDetailWithId {
  return { direction: 'in', icon: 'lu-arrow-down', identifier: 'receive', label: 'Receive', ...overrides };
}

function createWrapper(type: HistoryEventCategoryDetailWithId, highlight = false): VueWrapper {
  return mount(HistoryEventTypeCombination, {
    global: { stubs: { RuiIcon: true, RuiTooltip: true } },
    props: { highlight, type },
  });
}

function circleClasses(wrapper: VueWrapper): string[] {
  return wrapper.find('[data-testid=event-type-circle]').classes();
}

describe('modules/history/events/HistoryEventTypeCombination', () => {
  it('should tint the circle with the color of an incoming category', () => {
    const classes = circleClasses(createWrapper(createType({ color: 'success' })));

    expect(classes).toContain('bg-rui-success-soft');
    expect(classes).not.toContain('bg-rui-grey-200');
  });

  it('should tint the circle with the color of an outgoing category', () => {
    const classes = circleClasses(createWrapper(createType({ color: 'error', direction: 'out' })));

    expect(classes).toContain('bg-rui-error-soft');
  });

  it('should keep the grey circle for an uncolored category', () => {
    const classes = circleClasses(createWrapper(createType({ direction: 'neutral' })));

    expect(classes).toContain('bg-rui-grey-200');
  });

  it('should paint the highlight over the category tint', () => {
    const classes = circleClasses(createWrapper(createType({ color: 'success' }), true));

    expect(classes).toContain('bg-rui-primary-lighter/70');
    expect(classes).not.toContain('bg-rui-success-soft');
  });
});
