/**
 * The element ids the narrow list gives its rows and its footer examples.
 *
 * @remarks
 * The bar puts one of these in `aria-activedescendant` while the list renders the element it names,
 * so the two have to agree on both the prefix and the numbering. Neither side can check the other,
 * and a mismatch is silent: the attribute keeps pointing at an id that no longer exists, and the
 * list simply stops being reachable by keyboard. They are built here so there is one to agree with.
 *
 * @packageDocumentation
 */

/** Returns the id of the suggestion row at `index`. */
export function narrowRowId(index: number): string {
  return `pill-narrow-row-${index}`;
}

/** Returns the id of the footer syntax example at `index`. */
export function narrowExampleId(index: number): string {
  return `pill-narrow-example-${index}`;
}

/**
 * Returns the id of whatever a position in the combined arrow-navigable sequence lands on.
 *
 * @remarks
 * Rows come first and the footer examples follow, so a position at or past `rowCount` names an
 * example and is rebased onto the footer's own numbering. That offset lives here rather than at the
 * call site, since getting it wrong produces an id that exists but names the wrong element.
 *
 * @param index - the position in the combined sequence, rows then examples
 * @param rowCount - how many suggestion rows precede the footer
 */
export function narrowActiveId(index: number, rowCount: number): string {
  return index < rowCount ? narrowRowId(index) : narrowExampleId(index - rowCount);
}
