import type { VueWrapper } from '@vue/test-utils';

/** The attribute the e2e suite uses to find elements. */
const TEST_ID_ATTRIBUTE = 'data-testid';

/**
 * The test-id selectors a component renders, as `attribute=value`, deduplicated and sorted.
 *
 * The e2e suite drives the history event forms purely through these selectors, so the set a form
 * renders *is* its contract with `tests/e2e`. Snapshotting it turns "an e2e selector silently
 * disappeared during a refactor" into a millisecond-scale unit failure with a readable diff, instead
 * of a ten-minute e2e run that fails on a timeout somewhere unrelated.
 *
 *
 * Deliberately only the selector set: not the DOM, not the order, not the other attributes. Anything
 * finer would break on every markup tweak and get snapshot-updated without being read, which is the
 * exact failure mode that lets a real removal through.
 */
export function selectorContract(wrapper: VueWrapper<any>): string[] {
  const entries: string[] = [];

  const found: NodeListOf<Element> = wrapper.element.querySelectorAll(`[${TEST_ID_ATTRIBUTE}]`);
  for (const element of Array.from(found)) {
    const value = element.getAttribute(TEST_ID_ATTRIBUTE);
    if (value)
      entries.push(`${TEST_ID_ATTRIBUTE}=${value}`);
  }

  return Array.from(new Set(entries)).sort();
}
