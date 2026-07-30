import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';

/**
 * Drives the pill filter bar (`modules/core/table/pill/PillFilterBar.vue`).
 *
 * The bar is shared across tables, so this object knows nothing about history events —
 * callers pass the field keys (the wire keys, e.g. `counterparties`) their table exposes.
 */
export class PillFilterBar {
  constructor(private readonly page: Page) {}

  private get bar(): Locator {
    return this.page.locator('[data-testid=pill-bar]');
  }

  private get narrowInput(): Locator {
    return this.bar.locator('[data-testid=pill-narrow-input]');
  }

  async waitForVisible(): Promise<void> {
    await this.bar.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  /** The pill for a field, identified by the field key it renders (`data-field`). */
  pill(fieldKey: string): Locator {
    return this.page.locator(`[data-testid=filter-pill][data-field="${fieldKey}"]`);
  }

  async pillCount(): Promise<number> {
    return this.page.locator('[data-testid=filter-pill]').count();
  }

  /** The value segment's text, i.e. what the pill claims is filtered. */
  async pillValue(fieldKey: string): Promise<string> {
    return (await this.pill(fieldKey).locator('[data-testid=filter-pill-value]').innerText()).trim();
  }

  async expectPillVisible(fieldKey: string): Promise<void> {
    await expect(this.pill(fieldKey)).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  async expectNoPill(fieldKey: string): Promise<void> {
    await expect(this.pill(fieldKey)).toHaveCount(0, { timeout: TIMEOUT_MEDIUM });
  }

  /** Opens the `+ Add filter` menu without picking anything, for driving it by keyboard. */
  async openAddMenu(): Promise<void> {
    await this.bar.locator('[data-testid=pill-add]').click();
    await this.page
      .locator('[data-testid=pill-menu-search]')
      .waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  /**
   * Picks a field from the `+ Add filter` menu. The bar opens the new pill's value editor
   * straight away, so the editor is left open for the caller to fill in.
   */
  async addField(fieldKey: string): Promise<void> {
    await this.bar.locator('[data-testid=pill-add]').click();
    const option = this.page.locator(`[data-testid=pill-menu-field-${fieldKey}]`);
    await option.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await option.click();
  }

  /**
   * Ticks a value in the open enum/asset checklist. Multi-select fields stay open.
   *
   * The list is virtualized, so a value far down it is not in the DOM until the list is
   * narrowed — every selection goes through the search box first. Search matches the option's
   * *label*, so pass `search` explicitly whenever the label differs from the wire value
   * (`uniswap-v2` renders as `Uniswap V2`).
   */
  async selectValue(value: string, search?: string): Promise<void> {
    await this.searchValues(search ?? value);
    const option = this.page.locator(`[data-testid="value-select-option-${value}"]`);
    await option.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await option.click();
  }

  /**
   * Ticks a value only if it is not ticked already.
   *
   * `selectValue` clicks unconditionally, which toggles — fine when building a filter up from
   * nothing, wrong when the pill may already carry the value (a filter restored from the URL, say),
   * because unticking the last value drops the pill entirely.
   */
  async selectValueOnce(value: string, search?: string): Promise<void> {
    await this.searchValues(search ?? value);
    const option = this.page.locator(`[data-testid="value-select-option-${value}"]`);
    await option.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });

    if (await option.getAttribute('aria-checked') !== 'true')
      await option.click();
  }

  /** Types into the open checklist's search box (async lists such as assets need this). */
  async searchValues(query: string): Promise<void> {
    const search = this.page.locator('[data-testid=value-select-search]');
    await search.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await search.fill(query);
  }

  /** Types a value into the open free-text editor and commits it with Enter. */
  async typeTextValue(value: string): Promise<void> {
    const input = this.page.locator('[data-testid=text-input] input');
    await input.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await input.fill(value);
    await input.press('Enter');
  }

  /** Whether the open free-text editor considers what is typed a valid value. */
  async textValueIsValid(): Promise<boolean> {
    return this.page.locator('[data-testid=text-valid]').isVisible();
  }

  async setRangeBound(bound: 'min' | 'max', value: string): Promise<void> {
    const input = this.page.locator(`[data-testid=range-${bound}] input`);
    await input.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await input.fill(value);
  }

  /**
   * Commits the range with Enter, which also closes the editor.
   *
   * Typed bounds otherwise reach the filter through a 400ms debounce, so closing any other way
   * within that window discards them. Enter is the editor's explicit commit gesture.
   */
  async commitRange(bound: 'min' | 'max' = 'min'): Promise<void> {
    await this.page.locator(`[data-testid=range-${bound}] input`).press('Enter');
  }

  /** Switches the open editor's operator (`is not`, `greater than`, `before`, …). */
  async selectOperator(op: string): Promise<void> {
    const chip = this.page.locator(`[data-testid=op-${op}]`);
    await chip.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await chip.click();
  }

  /**
   * Types a `DD MM YYYY HH mm ss` digit run into one of the date bounds.
   *
   * The picker auto-advances between segments as digits arrive, and it opens a calendar popover
   * on focus, so the popover is dismissed afterwards or it covers whatever is clicked next.
   */
  async setDateBound(bound: 'from' | 'to', digits: string): Promise<void> {
    const input = this.page.locator(`[data-testid=date-${bound}] input`);
    await input.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await input.click({ position: { x: 1, y: 1 } });
    for (const digit of digits)
      await input.press(digit);
    await input.press('Escape');
  }

  /** Opens an existing pill's value editor. */
  async openPillEditor(fieldKey: string): Promise<void> {
    await this.pill(fieldKey).click();
  }

  /** The operator segment of a pill, absent when the field is on its default operator. */
  async pillText(fieldKey: string): Promise<string> {
    return (await this.pill(fieldKey).innerText()).trim();
  }

  /** Whether the open free-text editor is rejecting what is typed (invalid or already added). */
  async textFieldError(): Promise<string> {
    const editor = this.page.locator('[data-testid=text-input]');
    return (await editor.innerText()).trim();
  }

  /**
   * Closes an open checklist editor.
   *
   * The enum, asset and account editors have no `close` of their own — they rely on the menu
   * being dismissed. Escape usually does it, but it does not reach the asset editor while its
   * remote search is in flight, so passing the field key adds a deterministic fallback: clicking
   * the pill toggles its own menu shut. Selections in these editors commit on click, so nothing
   * is lost either way.
   */
  async closeEditor(fieldKey?: string): Promise<void> {
    // Whichever editor is open, its own first control stands in for it: there is no shared root to
    // wait on. Leaving one open matters beyond the editor itself, since its popover covers part of
    // the bar and swallows the next click.
    //
    // The date editor is deliberately absent: `RuiDateTimePicker` opens a calendar popover that
    // eats Escape, so its editor cannot be closed this way. `setDateBound` dismisses the calendar
    // itself, and the picker's keyboard handling is being fixed upstream in rotki/ui-library.
    const editor = this.page
      .locator([
        '[data-testid=value-select-search]',
        '[data-testid=text-input]',
        '[data-testid=range-min]',
      ].join(', '))
      .first();

    if (!(await editor.isVisible()))
      return;

    await this.page.keyboard.press('Escape');

    // The menu takes a moment to go, so give Escape time to work before falling back — clicking
    // the pill against an already-closing menu would just open it again.
    const closed = await editor
      .waitFor({ state: 'hidden', timeout: 2000 })
      .then(() => true)
      .catch(() => false);

    if (!closed && fieldKey)
      await this.pill(fieldKey).click();

    await expect(editor).toBeHidden({ timeout: TIMEOUT_MEDIUM });
  }

  /**
   * Dismisses whatever editor is open without an explicit commit gesture, the way clicking away
   * would. Closing is meant to commit, so anything typed must survive this.
   */
  async dismissEditor(): Promise<void> {
    await this.page.keyboard.press('Escape');
  }

  /** Asserts no editor is left open, with no fallback gesture to help it along. */
  async expectEditorClosed(): Promise<void> {
    await expect(this.page.locator('[data-testid=value-select-search]')).toBeHidden({ timeout: TIMEOUT_MEDIUM });
  }

  /**
   * Types into the bar's inline narrowing input one key at a time.
   *
   * `fill()` sets the value in a single shot and so cannot catch the class of bug where the
   * popover steals focus after the first keystroke — which is exactly how that bug once hid.
   */
  async narrow(query: string): Promise<void> {
    await this.narrowInput.click();
    await this.narrowInput.pressSequentially(query, { delay: 30 });
  }

  async clearNarrowInput(): Promise<void> {
    await this.narrowInput.fill('');
  }

  private suggestion(kind: 'field' | 'value', fieldKey: string, value?: string): Locator {
    const key = kind === 'field' ? `field-${fieldKey}` : `value-${fieldKey}-${value}`;
    return this.page.locator(`[data-testid="pill-narrow-${key}"]`);
  }

  /**
   * A whole filter read out of what was typed, identified by the operator it names: one query can
   * offer the same field twice, since a bare amount means either bound.
   */
  private filterSuggestion(fieldKey: string, op: string): Locator {
    return this.page.locator(`[data-testid="pill-narrow-filter-${fieldKey}-${op}"]`);
  }

  async expectFilterSuggestion(fieldKey: string, op: string): Promise<void> {
    await expect(this.filterSuggestion(fieldKey, op)).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  /**
   * Waits for a field to hold focus. An editor focuses its first input from `onMounted`, a tick
   * after the click that opened it has returned, so asserting focus straight away is a race.
   */
  async expectFocusedField(testId: string): Promise<void> {
    await expect.poll(async () => this.focusedFieldTestId(), { timeout: TIMEOUT_MEDIUM }).toBe(testId);
  }

  async hasFilterSuggestion(fieldKey: string, op: string): Promise<boolean> {
    return this.filterSuggestion(fieldKey, op).isVisible();
  }

  async filterSuggestionText(fieldKey: string, op: string): Promise<string> {
    return (await this.filterSuggestion(fieldKey, op).innerText()).replace(/\s+/g, ' ').trim();
  }

  async pickFilterSuggestion(fieldKey: string, op: string): Promise<void> {
    const row = this.filterSuggestion(fieldKey, op);
    await row.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await row.click();
  }

  async expectFieldSuggestion(fieldKey: string): Promise<void> {
    await expect(this.suggestion('field', fieldKey)).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  async expectValueSuggestion(fieldKey: string, value: string): Promise<void> {
    await expect(this.suggestion('value', fieldKey, value)).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  async pickFieldSuggestion(fieldKey: string): Promise<void> {
    const row = this.suggestion('field', fieldKey);
    await row.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await row.click();
  }

  async pickValueSuggestion(fieldKey: string, value: string): Promise<void> {
    const row = this.suggestion('value', fieldKey, value);
    await row.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await row.click();
  }

  /**
   * The first value suggestion offered for a field, whichever it happens to be.
   *
   * Asset rows arrive from a remote search whose ranking is not ours to predict — the same
   * symbol exists on many chains and the per-field cap keeps only the first few. A test about
   * the async path should assert that a row arrives and applies, not which row won.
   */
  async pickFirstValueSuggestion(fieldKey: string): Promise<void> {
    const row = this.page.locator(`[data-testid^="pill-narrow-value-${fieldKey}-"]`).first();
    await row.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await row.click();
  }

  async pressInNarrow(key: string): Promise<void> {
    await this.narrowInput.press(key);
  }

  /**
   * Moves the checklist highlight and toggles with the keyboard, from the search box that owns
   * focus while the list is open. Clicking rows cannot catch a menu that steals focus, which is
   * the way this editor has broken before.
   */
  async toggleHighlightedValue(steps: number = 1): Promise<void> {
    const search = this.page.locator('[data-testid=value-select-search]');
    for (let step = 0; step < steps; step++)
      await search.press('ArrowDown');
    await search.press('Enter');
  }

  /** `data-testid` of whatever currently holds focus, for asserting tab order. */
  async focusedTestId(): Promise<string | null> {
    return this.page.evaluate(() => document.activeElement?.getAttribute('data-testid') ?? null);
  }

  /** Presses a key against whatever currently holds focus, rather than a known element. */
  async pressFocused(key: string): Promise<void> {
    await this.page.keyboard.press(key);
  }

  /** Types into whatever currently holds focus, one key at a time. */
  async typeFocused(text: string): Promise<void> {
    await this.page.keyboard.type(text, { delay: 30 });
  }

  /**
   * `data-testid` of the nearest tagged ancestor of whatever holds focus.
   *
   * The editors put their test ids on a field wrapper rather than on the `<input>` inside it, so
   * `focusedTestId` reads null for them even when the right field has the caret.
   */
  async focusedFieldTestId(): Promise<string | null> {
    return this.page.evaluate(() =>
      document.activeElement?.closest('[data-testid]')?.getAttribute('data-testid') ?? null,
    );
  }

  /** Puts focus in the bar's inline input, the anchor for tabbing to the pills before it. */
  async focusNarrowInput(): Promise<void> {
    await this.narrowInput.click();
  }

  async removePill(fieldKey: string): Promise<void> {
    await this.pill(fieldKey).locator('[data-testid=filter-pill-remove]').click();
  }

  async clearAll(): Promise<void> {
    await this.bar.locator('[data-testid=pill-clear]').click();
  }

  /** The header's "1-10 of 24" summary, which is the only place the unpaged total is shown. */
  async pageRange(): Promise<string> {
    return (await this.page.locator('[data-testid=events-page-range]').innerText()).replace(/\s+/g, ' ').trim();
  }

  async nextPage(): Promise<void> {
    await this.page.locator('[data-testid=events-page-next]').click();
  }

  /** Toggles the date sort, the one column the events table can be sorted by. */
  async toggleDateSort(): Promise<void> {
    await this.page.locator('[data-testid=events-sort-date]').click();
  }
}
