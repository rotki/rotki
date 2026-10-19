import type { MaybeElementRef } from '@vueuse/core';
import type { InjectionKey, MaybeRefOrGetter, Ref } from 'vue';

const TableSelectionCollapsedKey: InjectionKey<Readonly<Ref<boolean>>> = Symbol('table-selection-collapsed');

/** What the bar knows about its own width on one measurement. */
interface CollapseMeasurement {
  collapsed: boolean;
  /** The width the bar's content needs laid out in one row, recorded when it last collapsed. */
  expandedWidth: number;
  clientWidth: number;
  scrollWidth: number;
}

interface CollapseDecision {
  collapsed: boolean;
  expandedWidth: number;
}

/**
 * Decides whether the bar's actions move into a menu.
 *
 * @remarks
 * Once collapsed the actions are no longer laid out, so the bar cannot see whether they would fit
 * again. It keeps the width the full row needed at the moment it collapsed and expands only once it
 * has at least that much room, which also stops it flickering between the two at the boundary.
 *
 * @returns the next collapsed state and the width to expand back at
 */
export function decideCollapse(measurement: CollapseMeasurement): CollapseDecision {
  const { clientWidth, collapsed, expandedWidth, scrollWidth } = measurement;
  if (!collapsed)
    return scrollWidth > clientWidth ? { collapsed: true, expandedWidth: scrollWidth } : { collapsed: false, expandedWidth };

  return { collapsed: clientWidth < expandedWidth, expandedWidth };
}

/**
 * Collapses a selection bar's actions into a menu while its row does not fit.
 *
 * @param target - the bar's root, laid out as a single row that is allowed to overflow
 * @param hasActions - whether there is anything to collapse; a bar without actions never does
 * @returns whether the actions are in the menu
 */
export function useSelectionBarCollapse(
  target: MaybeElementRef,
  hasActions: MaybeRefOrGetter<boolean>,
): Readonly<Ref<boolean>> {
  const collapsed = shallowRef<boolean>(false);
  let expandedWidth = 0;

  function measure(): void {
    const element = unrefElement(target);
    if (!element)
      return;

    if (!toValue(hasActions)) {
      set(collapsed, false);
      return;
    }

    const decision = decideCollapse({
      clientWidth: element.clientWidth,
      collapsed: get(collapsed),
      expandedWidth,
      scrollWidth: element.scrollWidth,
    });
    expandedWidth = decision.expandedWidth;
    set(collapsed, decision.collapsed);
  }

  useResizeObserver(target, measure);
  onUpdated(measure);

  return readonly(collapsed);
}

/**
 * Tells the actions inside a selection bar that they are in its overflow menu.
 *
 * @remarks
 * The actions are the consumer's slot content, so the bar cannot restyle them itself; each one reads
 * this instead and switches between an inline button and a menu entry.
 */
export function provideTableSelectionCollapsed(collapsed: Readonly<Ref<boolean>>): void {
  provide(TableSelectionCollapsedKey, collapsed);
}

/**
 * Whether the enclosing selection bar moved its actions into a menu.
 *
 * @returns `false` outside a bar, so an action still renders inline on its own
 */
export function useTableSelectionCollapsed(): Readonly<Ref<boolean>> {
  return inject(TableSelectionCollapsedKey, shallowRef<boolean>(false));
}
