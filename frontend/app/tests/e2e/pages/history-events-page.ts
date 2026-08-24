import type { Page } from '@playwright/test';
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
    await this.page.locator('[data-testid=history-events__add]').click();
    await this.page.locator('[data-testid=bottom-dialog]').waitFor({ state: 'visible' });
  }

  async selectEntryType(type: string): Promise<void> {
    const entryTypeSelect = this.page.locator('[data-testid=entry-type]');
    await entryTypeSelect.locator('[data-id=activator]').click();
    const menu = this.page.locator('[role=menu]');
    await menu.waitFor({ state: 'visible' });
    // RuiMenuSelect uses a virtual list — ensure the target option is rendered
    // by scrolling the internal scroller to the top before clicking.
    await menu.evaluate((el) => {
      const scrollers = el.querySelectorAll('*');
      for (const element of scrollers) {
        if (element instanceof HTMLElement && element.scrollHeight > element.clientHeight) {
          element.scrollTop = 0;
          return;
        }
      }
    });
    const option = menu.getByText(new RegExp(`^${type}$`, 'i'));
    await option.waitFor({ state: 'visible' });
    await option.click();
    await menu.waitFor({ state: 'hidden' });
  }

  private async fillDatetime(): Promise<void> {
    this.dateSequence++;
    const seconds = String(this.dateSequence).padStart(2, '0');
    // Format: DD MM YYYY HH mm ss SSS → 15/01/2024 12:00:XX.000
    const digits = `${TEST_EVENT_DATE_DIGITS}${seconds}000`;

    const input = this.page.locator('[data-testid=datetime] input');
    // Click at the far left to focus the first segment (DD).
    // The component uses cursor position to determine the active segment.
    await input.click({ position: { x: 1, y: 1 } });
    // Type digits — the component auto-advances between segments
    // (DD/MM/YYYY HH:mm:ss.SSS).
    for (const digit of digits)
      await input.press(digit);
    await input.press('Tab');
    // The datetime input opens a calendar popover on click; Tab does not
    // always close it. Press Escape and wait for the popover to detach so
    // the next form click is not intercepted by the calendar overlay.
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
    // Wait for the menu to close so the next activator click is not
    // intercepted by the still-visible menu overlay.
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
    // A field that already has a pill is no longer offered by the add menu, so re-filtering the
    // same field means editing its pill instead. Callers apply a location filter per test.
    if (await bar.pill(fieldKey).count() > 0)
      await bar.pill(fieldKey).click();
    else
      await bar.addField(fieldKey);

    // Ticking is a toggle, so a value the pill already carries would be turned back off, and an
    // emptied pill is dropped when the editor closes. Applying a filter has to be idempotent.
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
    // Wait for the dropdown menu to close so subsequent activator clicks
    // are not intercepted by the still-visible menu overlay.
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
