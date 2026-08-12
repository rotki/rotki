import { expect, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';
import { focusedAttribute, focusedFieldAttribute } from '../helpers/focused-element';

/**
 * The keyboard half of the pill filter bar: what holds focus, and what to press against it.
 *
 * Split out of `PillFilterBar` because it asserts about the document's focus rather than about the
 * bar's own elements, and because a test id now names a family: proving the right element has focus
 * takes both the id and the `data-key`/`data-index` beside it.
 */
export class PillFilterKeyboard {
  constructor(private readonly page: Page) {}

  /** `data-testid` of whatever currently holds focus, for asserting tab order. */
  async focusedTestId(): Promise<string | null> {
    return focusedAttribute(this.page, 'data-testid');
  }

  /**
   * The focused element's `data-index`. Rows carry their position here rather than in the test id,
   * so asserting the id alone would only prove "some row of this kind" has focus.
   */
  async focusedIndex(): Promise<string | null> {
    return focusedAttribute(this.page, 'data-index');
  }

  /**
   * `data-testid` of the nearest tagged ancestor of whatever holds focus.
   *
   * The editors put their test ids on a field wrapper rather than on the `<input>` inside it, so
   * `focusedTestId` reads null for them even when the right field has the caret.
   */
  async focusedFieldTestId(): Promise<string | null> {
    return focusedFieldAttribute(this.page, 'data-testid');
  }

  /** The `data-key` of the focused field's test-id element, for families that carry their value there. */
  async focusedFieldKey(): Promise<string | null> {
    return focusedFieldAttribute(this.page, 'data-key');
  }

  /**
   * Waits for a field to hold focus. An editor focuses its first input from `onMounted`, a tick
   * after the click that opened it has returned, so asserting focus straight away is a race.
   */
  async expectFocusedField(testId: string): Promise<void> {
    await expect.poll(async () => this.focusedFieldTestId(), { timeout: TIMEOUT_MEDIUM }).toBe(testId);
  }

  /**
   * Waits for a field to hold focus and to be the one named by `key`. The operator chips share the
   * `pill-op` id and tell themselves apart by `data-key`, so the id alone would only prove that
   * *some* chip has focus, not that Shift+Tab reached the last one.
   */
  async expectFocusedFieldKey(testId: string, key: string): Promise<void> {
    await this.expectFocusedField(testId);
    await expect.poll(async () => this.focusedFieldKey(), { timeout: TIMEOUT_MEDIUM }).toBe(key);
  }

  /** Presses a key against whatever currently holds focus, rather than a known element. */
  async pressFocused(key: string): Promise<void> {
    await this.page.keyboard.press(key);
  }

  /** Types into whatever currently holds focus, one key at a time. */
  async typeFocused(text: string): Promise<void> {
    await this.page.keyboard.type(text, { delay: 30 });
  }
}
