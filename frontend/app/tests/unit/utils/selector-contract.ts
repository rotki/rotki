import type { VueWrapper } from '@vue/test-utils';

/**
 * The attributes the e2e suite uses to find elements, in one place.
 *
 * `data-cy` is being retired in favour of `data-testid`, so both are collected: a form that has
 * already moved and one that has not are both covered, and when the rest migrate this list is the
 * only thing that changes.
 */
export const TEST_ID_ATTRIBUTES = ['data-cy', 'data-testid'] as const;

/**
 * The test-id selectors a component renders, as `attribute=value`, deduplicated and sorted.
 *
 * The e2e suite drives the history event forms purely through these selectors, so the set a form
 * renders *is* its contract with `tests/e2e`. Snapshotting it turns "an e2e selector silently
 * disappeared during a refactor" into a millisecond-scale unit failure with a readable diff, instead
 * of a ten-minute e2e run that fails on a timeout somewhere unrelated.
 *
 * The attribute is part of each entry on purpose: moving a field from `data-cy` to `data-testid`
 * breaks any e2e query still written against the old attribute, so it should fail here and force the
 * e2e side to be updated in the same change, rather than passing silently.
 *
 * Deliberately only the selector set: not the DOM, not the order, not the other attributes. Anything
 * finer would break on every markup tweak and get snapshot-updated without being read, which is the
 * exact failure mode that lets a real removal through.
 */
export function selectorContract(wrapper: VueWrapper<any>): string[] {
  const entries: string[] = [];

  for (const attribute of TEST_ID_ATTRIBUTES) {
    const found: NodeListOf<Element> = wrapper.element.querySelectorAll(`[${attribute}]`);
    for (const element of Array.from(found)) {
      const value = element.getAttribute(attribute);
      if (value)
        entries.push(`${attribute}=${value}`);
    }
  }

  return Array.from(new Set(entries)).sort();
}
