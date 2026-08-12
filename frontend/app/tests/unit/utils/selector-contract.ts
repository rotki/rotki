import type { VueWrapper } from '@vue/test-utils';

/** The attribute the e2e suite uses to find elements. */
const TEST_ID_ATTRIBUTE = 'data-testid';

/**
 * The attributes that carry the value a test id used to bake in, in selector order.
 *
 * A family is static now (`swap-sub-event-add`), so the id alone no longer tells the spend row from
 * the fee row. Without these the contract would collapse three selectors into one and stop noticing
 * if two of them disappeared.
 */
const VALUE_ATTRIBUTES = ['data-key', 'data-index'] as const;

/**
 * The test-id selectors a component renders, as `attribute=value`, deduplicated and sorted.
 *
 * The e2e suite drives the history event forms purely through these selectors, so the set a form
 * renders *is* its contract with `tests/e2e`. Snapshotting it turns "an e2e selector silently
 * disappeared during a refactor" into a millisecond-scale unit failure with a readable diff, instead
 * of a ten-minute e2e run that fails on a timeout somewhere unrelated.
 *
 *
 * Deliberately only the selector set: not the DOM, not the order, not every other attribute. Anything
 * finer would break on every markup tweak and get snapshot-updated without being read, which is the
 * exact failure mode that lets a real removal through. `data-key`/`data-index` are the exception,
 * because they carry the value the test id used to interpolate.
 */
export function selectorContract(wrapper: VueWrapper<any>): string[] {
  const entries: string[] = [];

  const found: NodeListOf<Element> = wrapper.element.querySelectorAll(`[${TEST_ID_ATTRIBUTE}]`);
  for (const element of Array.from(found)) {
    const value = element.getAttribute(TEST_ID_ATTRIBUTE);
    if (!value)
      continue;

    const qualifiers = VALUE_ATTRIBUTES
      .map(attribute => [attribute, element.getAttribute(attribute)] as const)
      .filter(([, held]) => held !== null)
      .map(([attribute, held]) => `[${attribute}=${held}]`)
      .join('');

    entries.push(`${TEST_ID_ATTRIBUTE}=${value}${qualifiers}`);
  }

  return Array.from(new Set(entries)).sort();
}
