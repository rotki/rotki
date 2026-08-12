import type { Page } from '@playwright/test';

/**
 * Reads an attribute off whatever currently holds focus.
 *
 * Test ids name a family and keep the value that used to be baked into them on `data-key` or
 * `data-index`, so a keyboard assertion usually needs two of these: the id proves *what kind* of
 * element has focus, the value proves *which one*.
 */
export async function focusedAttribute(page: Page, attribute: string): Promise<string | null> {
  return page.evaluate(name => document.activeElement?.getAttribute(name) ?? null, attribute);
}

/**
 * The same read, but from the focused element's nearest test-id ancestor.
 *
 * Rui form controls put focus on an inner `<input>` that carries no test id of its own, so reading
 * the active element directly returns null even when the right field has the caret.
 */
export async function focusedFieldAttribute(page: Page, attribute: string): Promise<string | null> {
  return page.evaluate(name => document.activeElement?.closest('[data-testid]')?.getAttribute(name) ?? null, attribute);
}
