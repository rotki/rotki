import type { Locator, Page } from '@playwright/test';
import { getValidSelectorFromEvmAddress } from '@rotki/common';
import {
  type AssetMovementEventFixture,
  type EthBlockEventFixture,
  type EthDepositEventFixture,
  type EthWithdrawalEventFixture,
  type EvmEventFixture,
  type EvmMultiSwapEventFixture,
  type EvmSwapEventFixture,
  type OnlineEventFixture,
  type SolanaEventFixture,
  type SolanaSwapEventFixture,
  type SwapEventFixture,
  TEST_EVENT_DATE_DIGITS,
} from '../fixtures/history-events';
import { TIMEOUT_LONG, TIMEOUT_MEDIUM } from '../helpers/constants';
import { selectAsset } from '../helpers/utils';
import { HistoryEventRows } from './history-event-rows';
import { PillFilterBar } from './pill-filter-bar';
import { RotkiApp } from './rotki-app';

/** One scroll step through a virtualised menu, comfortably inside one rendered window. */
const MENU_SCROLL_STEP = 150;

/** Time given to the virtual list to render the options at a new scroll offset. */
const MENU_RENDER_SETTLE_MS = 100;

export class HistoryEventsPage {
  private dateSequence = 0;

  /** Addressing, reading and acting on the table's rows. See `HistoryEventRows`. */
  readonly rows: HistoryEventRows;

  constructor(private readonly page: Page) {
    this.rows = new HistoryEventRows(page);
  }

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'history');
  }

  async openAddDialog(): Promise<void> {
    await this.page.locator('[data-testid=history-events-add]').click();
    await this.page.locator('[data-testid=bottom-dialog]').waitFor({ state: 'visible' });
  }

  async selectEntryType(type: string): Promise<void> {
    const entryTypeSelect = this.page.locator('[data-testid=entry-type]');
    await entryTypeSelect.locator('[data-id=activator]').click();
    const menu = this.page.locator('[role=menu]');
    await menu.waitFor({ state: 'visible' });
    const option = menu.getByText(new RegExp(`^${type}$`, 'i'));
    await this.scrollMenuUntilRendered(menu, option);
    await option.click();
    await menu.waitFor({ state: 'hidden' });
  }

  /**
   * Scrolls a virtualised RuiMenuSelect menu page by page until the option is rendered.
   *
   * @remarks
   * The menu renders only the options around the current scroll offset, so an option past the
   * first window (the entry-type list is alphabetical and longer than one window) never exists
   * in the DOM until the menu is scrolled to it.
   */
  private async scrollMenuUntilRendered(menu: Locator, option: Locator): Promise<void> {
    const scrollBy = async (offset: number): Promise<boolean> => menu.evaluate((el, delta) => {
      for (const element of el.querySelectorAll('*')) {
        if (element instanceof HTMLElement && element.scrollHeight > element.clientHeight) {
          const before = element.scrollTop;
          element.scrollTop = delta < 0 ? 0 : before + delta;
          return element.scrollTop !== before;
        }
      }
      return false;
    }, offset);

    await scrollBy(-1);
    let moved = true;
    while (!(await option.isVisible()) && moved) {
      moved = await scrollBy(MENU_SCROLL_STEP);
      if (moved) {
        await this.page.waitForTimeout(MENU_RENDER_SETTLE_MS);
      }
    }
    await option.waitFor({ state: 'visible' });
  }

  private async fillDatetime(): Promise<void> {
    this.dateSequence++;
    const seconds = String(this.dateSequence).padStart(2, '0');
    // Format: DD MM YYYY HH mm ss SSS → 15/01/2024 12:00:XX.000
    const digits = `${TEST_EVENT_DATE_DIGITS}${seconds}000`;

    const input = this.page.locator('[data-testid=datetime] input');
    // Cursor position picks the active segment, so the far left focuses DD.
    await input.click({ position: { x: 1, y: 1 } });
    // The component auto-advances between segments as the digits arrive.
    for (const digit of digits)
      await input.press(digit);
    await input.press('Tab');
    // Tab does not always close the calendar popover, which would intercept the next click.
    await input.press('Escape');
    await this.page.locator('[role=menu] h3').waitFor({ state: 'hidden', timeout: TIMEOUT_MEDIUM });
  }

  private async selectAutocompleteOption(dataTestid: string, value: string): Promise<void> {
    const field = this.page.locator(`[data-testid=${dataTestid}]`);
    await field.locator('[data-id=activator]').click();
    const menu = this.page.locator('[role=menu]').last();
    await menu.waitFor({ state: 'visible' });
    await field.locator('input').fill(value);
    const option = menu.getByText(value, { exact: false }).first();
    await option.waitFor({ state: 'visible' });
    await option.click();
    // A still-visible menu overlay would intercept the next activator click.
    await menu.waitFor({ state: 'hidden', timeout: TIMEOUT_MEDIUM });
  }

  private async selectAction(eventType: string, eventSubtype: string): Promise<void> {
    const picker = this.page.locator('[data-testid=event-action-picker]');
    await picker.locator('[data-id=activator]').click();
    const menu = this.page.locator('[role=menu]').last();
    await menu.waitFor({ state: 'visible' });
    const row = menu.locator(`[data-event-types~="${eventType}:${eventSubtype}"]`);
    await row.waitFor({ state: 'visible' });
    await row.click();
    await menu.waitFor({ state: 'hidden', timeout: TIMEOUT_MEDIUM });
  }

  private async selectLocation(location: string): Promise<void> {
    await this.selectAutocompleteOption('location', location);
  }

  async fillOnlineEventForm(data: OnlineEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.selectLocation(data.location);
    await this.selectAction(data.eventType, data.eventSubtype);
    await selectAsset(this.page, '[data-testid=asset]', data.asset, data.assetId);
    await this.page.locator('[data-testid=amount] input').clear();
    await this.page.locator('[data-testid=amount] input').fill(data.amount);
    await this.page.locator('[data-testid=notes] textarea:not([aria-hidden])').fill(data.notes);
  }

  async fillSwapEventForm(data: SwapEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.selectLocation(data.location);
    await selectAsset(this.page, '[data-testid=sub-event-asset][data-key=spend]', data.spendAsset, data.spendAssetId);
    await this.page.locator('[data-testid=sub-event-amount][data-key=spend] input').clear();
    await this.page.locator('[data-testid=sub-event-amount][data-key=spend] input').fill(data.spendAmount);
    await selectAsset(this.page, '[data-testid=sub-event-asset][data-key=receive]', data.receiveAsset, data.receiveAssetId);
    await this.page.locator('[data-testid=sub-event-amount][data-key=receive] input').clear();
    await this.page.locator('[data-testid=sub-event-amount][data-key=receive] input').fill(data.receiveAmount);

    if (data.fee) {
      await this.page.locator('[data-testid=has-fee]').click();
      await this.page.locator('[data-testid=fee-amount] input').clear();
      await this.page.locator('[data-testid=fee-amount] input').fill(data.fee.amount);
      await selectAsset(this.page, '[data-testid=fee-asset]', data.fee.asset, data.fee.assetId);
    }
  }

  async fillAssetMovementForm(data: AssetMovementEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.selectLocation(data.location);
    await this.selectAutocompleteOption('event-subtype', data.eventSubtype);
    await selectAsset(this.page, '[data-testid=asset]', data.asset, data.assetId);
    await this.page.locator('[data-testid=amount] input').clear();
    await this.page.locator('[data-testid=amount] input').fill(data.amount);
    await this.page.locator('[data-testid=notes] textarea:not([aria-hidden])').fill(data.notes);
  }

  async saveForm(): Promise<void> {
    await this.page.locator('[data-testid=bottom-dialog] [data-testid=confirm]').click();
    await this.page.locator('[data-testid=bottom-dialog]').waitFor({ state: 'detached', timeout: TIMEOUT_LONG });
  }

  /**
   * Applies a single-value filter through the pill bar.
   *
   * `fieldKey` is the wire key the pill bar uses (`location`, `eventTypes`, …), and `value` is
   * the raw wire value. Callers that only need "filter this table down" should use this; the
   * pill bar's own behaviour is covered by `specs/history/pill-filter.spec.ts`.
   */
  async applyTableFilter(fieldKey: string, value: string): Promise<void> {
    const bar = new PillFilterBar(this.page);
    // The add menu drops a field that already has a pill, so re-filtering edits the pill.
    if (await bar.pill(fieldKey).count() > 0)
      await bar.pill(fieldKey).click();
    else
      await bar.addField(fieldKey);

    // Ticking toggles, so re-ticking a carried value would empty the pill and drop it.
    await bar.selectValueOnce(value);
    await bar.closeEditor();
    await bar.expectPillVisible(fieldKey);
  }

  private async fillAddressAutocomplete(dataTestid: string, address: string): Promise<void> {
    const field = this.page.locator(`[data-testid=${dataTestid}]`);
    await field.locator('input').click();
    await field.locator('input').fill(address);
    // Allow custom value entry by pressing Enter
    await this.page.keyboard.press('Enter');
  }

  async fillSolanaEventForm(data: SolanaEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.page.locator('[data-testid=tx-ref] input').fill(data.txRef);
    await this.selectAction(data.eventType, data.eventSubtype);
    await selectAsset(this.page, '[data-testid=asset]', data.asset, data.assetId);
    await this.page.locator('[data-testid=amount] input').clear();
    await this.page.locator('[data-testid=amount] input').fill(data.amount);
    await this.page.locator('[data-testid=notes] textarea:not([aria-hidden])').fill(data.notes);
  }

  async fillSolanaSwapEventForm(data: SolanaSwapEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.page.locator('[data-testid=tx-ref] input').click();
    await this.page.locator('[data-testid=tx-ref] input').fill(data.txRef);
    await selectAsset(this.page, '[data-testid=sub-event-asset][data-key=spend]', data.spendAsset, data.spendAssetId);
    await this.page.locator('[data-testid=sub-event-amount][data-key=spend] input').clear();
    await this.page.locator('[data-testid=sub-event-amount][data-key=spend] input').fill(data.spendAmount);
    await selectAsset(this.page, '[data-testid=sub-event-asset][data-key=receive]', data.receiveAsset, data.receiveAssetId);
    await this.page.locator('[data-testid=sub-event-amount][data-key=receive] input').clear();
    await this.page.locator('[data-testid=sub-event-amount][data-key=receive] input').fill(data.receiveAmount);
  }

  async fillEthBlockEventForm(data: EthBlockEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.page.locator('[data-testid=block-number] input').clear();
    await this.page.locator('[data-testid=block-number] input').fill(data.blockNumber);
    await this.page.locator('[data-testid=validator-index] input').clear();
    await this.page.locator('[data-testid=validator-index] input').fill(data.validatorIndex);
    await this.page.locator('[data-testid=amount] input').clear();
    await this.page.locator('[data-testid=amount] input').fill(data.amount);
    await this.fillAddressAutocomplete('fee-recipient', data.feeRecipient);

    if (data.isMevReward)
      await this.page.locator('[data-testid=is-mev-reward]').click();
  }

  async fillEthWithdrawalEventForm(data: EthWithdrawalEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.page.locator('[data-testid=validator-index] input').clear();
    await this.page.locator('[data-testid=validator-index] input').fill(data.validatorIndex);
    await this.page.locator('[data-testid=amount] input').clear();
    await this.page.locator('[data-testid=amount] input').fill(data.amount);
    await this.fillAddressAutocomplete('withdrawal-address', data.withdrawalAddress);

    if (data.isExit)
      await this.page.locator('[data-testid=is-exit]').click();
  }

  async fillEthDepositEventForm(data: EthDepositEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.page.locator('[data-testid=validator-index] input').clear();
    await this.page.locator('[data-testid=validator-index] input').fill(data.validatorIndex);
    await this.page.locator('[data-testid=tx-ref] input').fill(data.txHash);
    await this.page.locator('[data-testid=amount] input').clear();
    await this.page.locator('[data-testid=amount] input').fill(data.amount);
    await this.fillAddressAutocomplete('depositor', data.depositor);
    // Click outside to dismiss any autocomplete dropdown and trigger blur validation
    await this.page.locator('[data-testid=tx-ref] input').click();
  }

  async fillEvmEventForm(data: EvmEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.selectLocation('ethereum');
    await this.page.locator('[data-testid=tx-ref] input').fill(data.txRef);
    await this.selectAction(data.eventType, data.eventSubtype);
    await selectAsset(this.page, '[data-testid=asset]', data.asset, data.assetId);
    await this.page.locator('[data-testid=amount] input').clear();
    await this.page.locator('[data-testid=amount] input').fill(data.amount);
    await this.page.locator('[data-testid=notes] textarea:not([aria-hidden])').fill(data.notes);
  }

  async fillEvmSwapEventForm(data: EvmSwapEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.selectLocation('ethereum');
    await this.page.locator('[data-testid=tx-ref] input').fill(data.txRef);
    await selectAsset(this.page, '[data-testid=sub-event-asset][data-key=spend]', data.spendAsset, data.spendAssetId);
    await this.page.locator('[data-testid=sub-event-amount][data-key=spend] input').clear();
    await this.page.locator('[data-testid=sub-event-amount][data-key=spend] input').fill(data.spendAmount);
    await selectAsset(this.page, '[data-testid=sub-event-asset][data-key=receive]', data.receiveAsset, data.receiveAssetId);
    await this.page.locator('[data-testid=sub-event-amount][data-key=receive] input').clear();
    await this.page.locator('[data-testid=sub-event-amount][data-key=receive] input').fill(data.receiveAmount);
  }

  private async selectNthAsset(
    selector: string,
    index: number,
    value: string,
    id?: string,
  ): Promise<void> {
    const container = this.page.locator(selector).nth(index);
    await container.locator('[data-id=activator]').click();
    await container.locator('input').fill(value);
    const identifier = getValidSelectorFromEvmAddress((id ?? value).toLocaleLowerCase());
    const option = this.page.locator(`#asset-${identifier}`);
    await option.click();
    // A still-visible menu overlay would intercept the next activator click.
    await option.waitFor({ state: 'hidden', timeout: TIMEOUT_MEDIUM });
  }

  private async fillSubEventList(
    type: 'spend' | 'receive' | 'fee',
    items: { asset: string; assetId?: string; amount: string }[],
  ): Promise<void> {
    for (const [i, item] of items.entries()) {
      if (i > 0)
        await this.page.locator(`[data-testid=swap-sub-event-add][data-key=${type}]`).click();

      const amount = `[data-testid=sub-event-amount][data-key=${type}]`;
      await this.selectNthAsset(`[data-testid=sub-event-asset][data-key=${type}]`, i, item.asset, item.assetId);
      await this.page.locator(`${amount} input`).nth(i).clear();
      await this.page.locator(`${amount} input`).nth(i).fill(item.amount);
    }
  }

  async getExpandedEventRows(): Promise<number> {
    return this.page.locator('[data-testid=history-event-row]').count();
  }

  async deleteSubEvent(index: number): Promise<void> {
    const row = this.page.locator('[data-testid=history-event-row]').nth(index);
    await row.hover();
    await row.locator('[data-testid=row-delete]').click();
    const dialog = this.page.locator('[data-testid=confirm-dialog]');
    await dialog.locator('[data-testid=button-confirm]').click();
    await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
  }

  async fillEvmMultiSwapEventForm(data: EvmMultiSwapEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.selectLocation('ethereum');
    await this.page.locator('[data-testid=tx-ref] input').fill(data.txRef);

    await this.fillSubEventList('spend', data.spend);
    await this.fillSubEventList('receive', data.receive);

    if (data.fees.length > 0) {
      await this.page.locator('[data-testid=has-fee]').click();
      await this.fillSubEventList('fee', data.fees);
    }
  }
}
