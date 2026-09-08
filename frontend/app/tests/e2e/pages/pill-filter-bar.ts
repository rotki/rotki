import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';
import { PillFilterKeyboard } from './pill-filter-keyboard';

/**
 * Drives the pill filter bar (`modules/core/table/pill/PillFilterBar.vue`).
 *
 * The bar is shared across tables, so this object knows nothing about history events —
 * callers pass the field keys (the wire keys, e.g. `counterparties`) their table exposes.
 */
export class PillFilterBar {
  /** Focus reads and key presses, which are about the document rather than about the bar. */
  readonly keyboard: PillFilterKeyboard;

  constructor(private readonly page: Page) {
    this.keyboard = new PillFilterKeyboard(page);
  }

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

  async expectPillCount(expected: number): Promise<void> {
    await expect(this.page.locator('[data-testid=filter-pill]')).toHaveCount(expected, { timeout: TIMEOUT_MEDIUM });
  }

  /** The value segment, i.e. what the pill claims is filtered. */
  private pillValue(fieldKey: string): Locator {
    return this.pill(fieldKey).locator('[data-testid=filter-pill-value]');
  }

  async expectPillValue(fieldKey: string, text: string): Promise<void> {
    await expect(this.pillValue(fieldKey)).toContainText(text, { timeout: TIMEOUT_MEDIUM });
  }

  /** The overflow counter is absent below the threshold, so its absence is what a test pins. */
  async expectPillValueMissing(fieldKey: string, text: string): Promise<void> {
    await expect(this.pillValue(fieldKey)).not.toContainText(text, { timeout: TIMEOUT_MEDIUM });
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
    const option = this.page.locator(`[data-testid=pill-menu-field][data-field="${fieldKey}"]`);
    await option.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await option.click();
  }

  /**
   * Ticks a value in the open enum/asset checklist. Multi-select fields stay open.
   *
   * The list is virtualized, so a value far down it is not in the DOM until the list is
   * narrowed — every selection goes through the search box first. Search matches the option's
   * label*, so pass `search` explicitly whenever the label differs from the wire value
   * (`uniswap-v2` renders as `Uniswap V2`).
   *
   * Narrowing is only enough when the query names the value. On the asset field the search runs
   * remotely and returns up to fifty ranked results, so a query matching many assets equally well
   * (a symbol several chains share) leaves the intended one somewhere in the list but outside the
   * rendered window, and this waits for a row that never appears. Search such a field by
   * identifier or address, which the app parses into an exact address lookup.
   */
  async selectValue(value: string, search?: string): Promise<void> {
    await this.searchValues(search ?? value);
    const option = this.page.locator(`[data-testid=value-select-option][data-key="${value}"]`);
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
    const option = this.page.locator(`[data-testid=value-select-option][data-key="${value}"]`);
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

  /**
   * The open free-text editor rejects what is typed.
   *
   * @remarks
   * Validity is recomputed as the value changes, so the marker appears and disappears a tick behind
   * the typing that drives it.
   */
  async expectTextValueInvalid(): Promise<void> {
    await expect(this.page.locator('[data-testid=text-valid]')).toBeHidden({ timeout: TIMEOUT_MEDIUM });
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
    const chip = this.page.locator(`[data-testid=pill-op][data-key="${op}"]`);
    await chip.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await chip.click();
  }

  /**
   * Types a `DD MM YYYY HH mm ss` digit run into one of the date bounds.
   *
   * The picker auto-advances between segments as digits arrive, and it opens a calendar popover
   * on focus, so the popover is dismissed afterwards or it covers whatever is clicked next.
   *
   * That escape only closes the calendar: it never reaches the field itself, so a bound left
   * incomplete is not committed here. A full entry is already a value the moment its last digit
   * lands, but a bare date is written when the field is done with - setting the other bound blurs
   * this one, and `closeEditor` sends the press that finishes the last one.
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

  /** The whole pill, including the operator segment that is absent on the default operator. */
  async expectPillText(fieldKey: string, text: string): Promise<void> {
    await expect(this.pill(fieldKey)).toContainText(text, { timeout: TIMEOUT_MEDIUM });
  }

  /** What the open free-text editor says about the value: invalid, or already added. */
  async expectTextFieldError(text: string | RegExp): Promise<void> {
    await expect(this.page.locator('[data-testid=text-input]')).toContainText(text, { timeout: TIMEOUT_MEDIUM });
  }

  /**
   * Closes an open checklist editor.
   *
   * The enum, asset and account editors have no `close` of their own — they rely on the menu
   * being dismissed. Escape usually does it, but it does not reach the asset editor while its
   * remote search is in flight, so passing the field key adds a deterministic fallback: clicking
   * the pill toggles its own menu shut. Selections in these editors commit on click, so nothing
   * is lost either way.
   *
   * There is no shared root to wait on, so whichever editor is open stands in through its own
   * first control. An editor left open covers part of the bar and swallows the next click. The
   * date editor takes two presses, and `setDateBound` has spent the first on the picker's
   * calendar, so the press here is the one `DateValueEditor` sees, and the one that commits a
   * bound typed as a bare date.
   */
  async closeEditor(fieldKey?: string): Promise<void> {
    const editor = this.page
      .locator([
        '[data-testid=value-select-search]',
        '[data-testid=text-input]',
        '[data-testid=range-min]',
        '[data-testid=date-from] input',
        '[data-testid=date-to] input',
      ].join(', '))
      .first();

    if (!(await editor.isVisible()))
      return;

    await this.page.keyboard.press('Escape');

    // Clicking the pill against an already-closing menu would just open it again.
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
    return this.page.locator(`[data-testid=pill-narrow-row][data-key="${key}"]`);
  }

  /**
   * A whole filter read out of what was typed, identified by the operator it names: one query can
   * offer the same field twice, since a bare amount means either bound.
   */
  private filterSuggestion(fieldKey: string, op: string): Locator {
    return this.page.locator(`[data-testid=pill-narrow-row][data-key="filter-${fieldKey}-${op}"]`);
  }

  async expectFilterSuggestion(fieldKey: string, op: string): Promise<void> {
    await expect(this.filterSuggestion(fieldKey, op)).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  async expectNoFilterSuggestion(fieldKey: string, op: string): Promise<void> {
    await expect(this.filterSuggestion(fieldKey, op)).toBeHidden({ timeout: TIMEOUT_MEDIUM });
  }

  async expectFilterSuggestionText(fieldKey: string, op: string, text: string): Promise<void> {
    await expect(this.filterSuggestion(fieldKey, op)).toContainText(text, { timeout: TIMEOUT_MEDIUM });
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
    const row = this.page.locator(`[data-testid=pill-narrow-row][data-key^="value-${fieldKey}-"]`).first();
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
  async expectPageRange(text: string): Promise<void> {
    await expect(this.page.locator('[data-testid=events-page-range]')).toContainText(text, { timeout: TIMEOUT_MEDIUM });
  }

  async nextPage(): Promise<void> {
    await this.page.locator('[data-testid=events-page-next]').click();
  }

  /** Toggles the date sort, the one column the events table can be sorted by. */
  async toggleDateSort(): Promise<void> {
    await this.page.locator('[data-testid=events-sort-date]').click();
  }
}
