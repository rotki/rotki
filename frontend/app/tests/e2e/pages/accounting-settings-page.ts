import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';
import { confirmInlineSuccess } from '../helpers/utils';

export class AccountingSettingsPage {
  constructor(private readonly page: Page) {}

  private get rulesTable(): Locator {
    return this.page.locator('[data-testid=accounting-rule-table]');
  }

  /**
   * How many rules are on the page, counted by their type cell rather than by `tr`: an empty table
   * still renders one row, the "no data" one, so counting rows reads 1 for a filter that matched
   * nothing.
   */
  async ruleCount(): Promise<number> {
    return this.rulesTable.locator('[data-testid=accounting-rule-event-type]').count();
  }

  /**
   * The event type each visible rule is for. Read as a set of values rather than by row index: the
   * order the backend returns rules in is not part of what a filter test is asserting.
   */
  async visibleEventTypes(): Promise<string[]> {
    const cells = await this.rulesTable.locator('[data-testid=accounting-rule-event-type]').allInnerTexts();
    return cells.map(text => text.replace(/\s*-\s*$/, '').trim());
  }

  /**
   * Waits for the table to hold rules at all. Polled: the table renders before its first page
   * arrives, so anything read straight after a click sees the empty table it started as.
   */
  async expectRules(): Promise<void> {
    await this.rulesTable.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await expect.poll(async () => this.ruleCount(), { timeout: TIMEOUT_MEDIUM }).toBeGreaterThan(0);
  }

  async expectNoRules(): Promise<void> {
    await this.rulesTable.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await expect.poll(async () => this.ruleCount(), { timeout: TIMEOUT_MEDIUM }).toBe(0);
  }

  /**
   * Asserts every visible rule is for this event type, and that there is at least one — an empty
   * table trivially satisfies "all of them match".
   */
  async expectOnlyEventType(eventType: string): Promise<void> {
    await expect
      .poll(async () => [...new Set(await this.visibleEventTypes())].sort(), { timeout: TIMEOUT_MEDIUM })
      .toStrictEqual([eventType]);
  }

  /**
   * Waits until a rule of this event type is on the page.
   *
   * Polled rather than read once: the table keeps showing the previous filter's rules until the
   * next response lands, so a single read after clearing a filter can still see them.
   */
  async expectEventTypePresent(eventType: string): Promise<void> {
    await expect
      .poll(async () => this.visibleEventTypes(), { timeout: TIMEOUT_MEDIUM })
      .toContain(eventType);
  }

  /**
   * Switches between the general rules and the rules written for one event each, and waits for the
   * rules the new tab asked for to arrive.
   *
   * The wait is the whole point: the table is keyed on the tab, so switching remounts it with zero
   * rows *before* the request is sent. Asserting on the table without waiting therefore reads the
   * empty table the switch itself produced, and "the custom tab has no rules" passes whatever the
   * backend returns.
   */
  async selectRuleTab(tab: 'regular' | 'custom'): Promise<void> {
    const [response] = await Promise.all([
      this.page.waitForResponse(response =>
        response.url().includes('/accounting/rules') && response.request().method() === 'POST'),
      this.page.locator(`[data-testid=accounting-rule-tab-${tab}]`).click(),
    ]);

    // What the tab is *for*: it asks the backend for one half of the rules. Asserted on the request
    // because both halves can legitimately be empty, and then the rendered table says nothing about
    // whether the tab did anything at all.
    const expected = tab === 'custom' ? 'only' : 'exclude';
    expect(response.request().postDataJSON()).toMatchObject({ custom_rule_handling: expected });
  }

  async visit(): Promise<void> {
    await this.page.locator('[data-testid=user-menu-button]').click();
    await this.page.locator('[data-testid=user-dropdown]').waitFor({ state: 'visible' });
    await this.page.locator('[data-testid=settings-button]').click();
    await this.page.locator('[data-testid=user-dropdown]').waitFor({ state: 'detached' });
    await this.page.locator('[data-testid="settings__accounting"]').click();
    await this.page.locator('[data-testid=crypto2crypto-switch]').waitFor({ state: 'visible' });
  }

  async setTaxFreePeriodDays(value: string): Promise<void> {
    await this.page.locator('[data-testid=taxfree-period] input').clear();
    await this.page.locator('[data-testid=taxfree-period] input').fill(value);
    await this.page.locator('[data-testid=taxfree-period] input').blur();
    await confirmInlineSuccess(this.page, '[data-testid=taxfree-period] .details', value);
  }

  async changeSwitch(target: string, enabled: boolean): Promise<void> {
    await this.page.locator(target).scrollIntoViewIfNeeded();
    await this.page.locator(target).waitFor({ state: 'visible' });
    await this.verifySwitchState(target, !enabled);
    await this.page.locator(`${target} input`).click();
    await this.verifySwitchState(target, enabled);
    await confirmInlineSuccess(this.page, `${target} .details .text-rui-success`);
  }

  async verifySwitchState(target: string, enabled: boolean): Promise<void> {
    if (enabled) {
      await expect(this.page.locator(`${target} input`)).toBeChecked();
    }
    else {
      await expect(this.page.locator(`${target} input`)).not.toBeChecked();
    }
  }
}
