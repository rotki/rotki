import { expect, type Page } from '@playwright/test';
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
import { RotkiApp } from './rotki-app';

export class HistoryEventsPage {
  private dateSequence = 0;

  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'history');
  }

  async openAddDialog(): Promise<void> {
    await this.page.locator('[data-cy=history-events__add]').click();
    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'visible' });
  }

  async selectEntryType(type: string): Promise<void> {
    const entryTypeSelect = this.page.locator('[data-cy=entry-type]');
    await entryTypeSelect.click();
    const menu = this.page.locator('[role=menu]');
    await menu.waitFor({ state: 'visible' });
    await menu.getByText(new RegExp(`^${type}$`, 'i')).click();
    await menu.waitFor({ state: 'hidden' });
  }

  private async fillDatetime(): Promise<void> {
    this.dateSequence++;
    const seconds = String(this.dateSequence).padStart(2, '0');
    // Format: DD MM YYYY HH mm ss SSS → 15/01/2024 12:00:XX.000
    const digits = `${TEST_EVENT_DATE_DIGITS}${seconds}000`;

    const input = this.page.locator('[data-cy=datetime] input');
    // Click at the far left to focus the first segment (DD).
    // The component uses cursor position to determine the active segment.
    await input.click({ position: { x: 1, y: 1 } });
    // Type digits — the component auto-advances between segments
    // (DD/MM/YYYY HH:mm:ss.SSS).
    for (const digit of digits)
      await input.press(digit);
    await input.press('Tab');
  }

  private async selectAutocompleteOption(dataCy: string, value: string): Promise<void> {
    const field = this.page.locator(`[data-cy=${dataCy}]`);
    await field.locator('[data-id=activator]').click();
    const menu = this.page.locator('[role=menu]').last();
    await menu.waitFor({ state: 'visible' });
    await field.locator('input').fill(value);
    const option = menu.getByText(value, { exact: false }).first();
    await option.waitFor({ state: 'visible' });
    await option.click();
  }

  private async selectLocation(location: string): Promise<void> {
    await this.selectAutocompleteOption('location', location);
  }

  async fillOnlineEventForm(data: OnlineEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.selectLocation(data.location);
    await this.selectAutocompleteOption('eventType', data.eventType);
    await this.selectAutocompleteOption('eventSubtype', data.eventSubtype);
    await selectAsset(this.page, '[data-cy=asset]', data.asset, data.assetId);
    await this.page.locator('[data-cy=amount] input').clear();
    await this.page.locator('[data-cy=amount] input').fill(data.amount);
    await this.page.locator('[data-cy=notes] textarea:not([aria-hidden])').fill(data.notes);
  }

  async fillSwapEventForm(data: SwapEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.selectLocation(data.location);
    await selectAsset(this.page, '[data-cy=spend-asset]', data.spendAsset, data.spendAssetId);
    await this.page.locator('[data-cy=spend-amount] input').clear();
    await this.page.locator('[data-cy=spend-amount] input').fill(data.spendAmount);
    await selectAsset(this.page, '[data-cy=receive-asset]', data.receiveAsset, data.receiveAssetId);
    await this.page.locator('[data-cy=receive-amount] input').clear();
    await this.page.locator('[data-cy=receive-amount] input').fill(data.receiveAmount);

    if (data.fee) {
      await this.page.locator('[data-cy=has-fee]').click();
      await this.page.locator('[data-cy=fee-amount] input').clear();
      await this.page.locator('[data-cy=fee-amount] input').fill(data.fee.amount);
      await selectAsset(this.page, '[data-cy=fee-asset]', data.fee.asset, data.fee.assetId);
    }
  }

  async fillAssetMovementForm(data: AssetMovementEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.selectLocation(data.location);
    await this.selectAutocompleteOption('eventSubtype', data.eventSubtype);
    await selectAsset(this.page, '[data-cy=asset]', data.asset, data.assetId);
    await this.page.locator('[data-cy=amount] input').clear();
    await this.page.locator('[data-cy=amount] input').fill(data.amount);
    await this.page.locator('[data-cy=notes] textarea:not([aria-hidden])').fill(data.notes);
  }

  async saveForm(): Promise<void> {
    await this.page.locator('[data-cy=bottom-dialog] [data-cy=confirm]').click();
    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'detached', timeout: TIMEOUT_LONG });
  }

  async getEventRows(): Promise<number> {
    const rows = this.page.locator('[data-cy=history-event-row]');
    return rows.count();
  }

  async getSwapRows(): Promise<number> {
    const rows = this.page.locator('[data-cy=history-event-swap]');
    return rows.count();
  }

  async getMovementRows(): Promise<number> {
    const rows = this.page.locator('[data-cy=history-event-movement]');
    return rows.count();
  }

  async verifyEventTypeLabel(rowSelector: string, index: number, expectedText: string): Promise<void> {
    const row = this.page.locator(rowSelector).nth(index);
    const eventType = row.locator('[data-cy=event-type]');
    await expect(eventType).toContainText(expectedText, { timeout: TIMEOUT_MEDIUM });
  }

  async verifyEventNotes(rowSelector: string, index: number, expectedNotes: string): Promise<void> {
    const row = this.page.locator(rowSelector).nth(index);
    const notes = row.locator('[data-cy=event-notes]');
    await expect(notes).toContainText(expectedNotes, { timeout: TIMEOUT_MEDIUM });
  }

  async verifyEventAmount(rowSelector: string, index: number, expectedAmount: string): Promise<void> {
    const row = this.page.locator(rowSelector).nth(index);
    const amount = row.locator('[data-cy=event-amount]').first();
    await expect(amount).toContainText(expectedAmount, { timeout: TIMEOUT_MEDIUM });
  }

  async editEvent(rowSelector: string, index: number): Promise<void> {
    const row = this.page.locator(rowSelector).nth(index);
    await row.hover();
    await row.locator('[data-cy=row-edit]').click();
    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'visible' });
  }

  async deleteEvent(rowSelector: string, index: number): Promise<void> {
    const row = this.page.locator(rowSelector).nth(index);
    await row.hover();
    await row.locator('[data-cy=row-delete]').click();
    // Confirm the delete dialog
    const dialog = this.page.locator('[data-cy=confirm-dialog]');
    await dialog.locator('[data-cy=button-confirm]').click();
    await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
  }

  private async fillAddressAutocomplete(dataCy: string, address: string): Promise<void> {
    const field = this.page.locator(`[data-cy=${dataCy}]`);
    await field.locator('input').click();
    await field.locator('input').fill(address);
    // Allow custom value entry by pressing Enter
    await this.page.keyboard.press('Enter');
  }

  async fillSolanaEventForm(data: SolanaEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.page.locator('[data-cy=tx-ref] input').fill(data.txRef);
    await this.selectAutocompleteOption('eventType', data.eventType);
    await this.selectAutocompleteOption('eventSubtype', data.eventSubtype);
    await selectAsset(this.page, '[data-cy=asset]', data.asset, data.assetId);
    await this.page.locator('[data-cy=amount] input').clear();
    await this.page.locator('[data-cy=amount] input').fill(data.amount);
    await this.page.locator('[data-cy=notes] textarea:not([aria-hidden])').fill(data.notes);
  }

  async fillSolanaSwapEventForm(data: SolanaSwapEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.page.locator('[data-cy=tx-ref] input').fill(data.txRef);
    await selectAsset(this.page, '[data-cy=spend-asset]', data.spendAsset, data.spendAssetId);
    await this.page.locator('[data-cy=spend-amount] input').clear();
    await this.page.locator('[data-cy=spend-amount] input').fill(data.spendAmount);
    await selectAsset(this.page, '[data-cy=receive-asset]', data.receiveAsset, data.receiveAssetId);
    await this.page.locator('[data-cy=receive-amount] input').clear();
    await this.page.locator('[data-cy=receive-amount] input').fill(data.receiveAmount);
  }

  async fillEthBlockEventForm(data: EthBlockEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.page.locator('[data-cy=blockNumber] input').clear();
    await this.page.locator('[data-cy=blockNumber] input').fill(data.blockNumber);
    await this.page.locator('[data-cy=validatorIndex] input').clear();
    await this.page.locator('[data-cy=validatorIndex] input').fill(data.validatorIndex);
    await this.page.locator('[data-cy=amount] input').clear();
    await this.page.locator('[data-cy=amount] input').fill(data.amount);
    await this.fillAddressAutocomplete('feeRecipient', data.feeRecipient);

    if (data.isMevReward)
      await this.page.locator('[data-cy=isMevReward]').click();
  }

  async fillEthWithdrawalEventForm(data: EthWithdrawalEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.page.locator('[data-cy=validatorIndex] input').clear();
    await this.page.locator('[data-cy=validatorIndex] input').fill(data.validatorIndex);
    await this.page.locator('[data-cy=amount] input').clear();
    await this.page.locator('[data-cy=amount] input').fill(data.amount);
    await this.fillAddressAutocomplete('withdrawalAddress', data.withdrawalAddress);

    if (data.isExit)
      await this.page.locator('[data-cy=is-exit]').click();
  }

  async fillEthDepositEventForm(data: EthDepositEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.page.locator('[data-cy=validatorIndex] input').clear();
    await this.page.locator('[data-cy=validatorIndex] input').fill(data.validatorIndex);
    await this.page.locator('[data-cy=tx-ref] input').fill(data.txHash);
    await this.page.locator('[data-cy=amount] input').clear();
    await this.page.locator('[data-cy=amount] input').fill(data.amount);
    await this.fillAddressAutocomplete('depositor', data.depositor);
    // Click outside to dismiss any autocomplete dropdown and trigger blur validation
    await this.page.locator('[data-cy=tx-ref] input').click();
  }

  async fillEvmEventForm(data: EvmEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.selectLocation('ethereum');
    await this.page.locator('[data-cy=tx-ref] input').fill(data.txRef);
    await this.selectAutocompleteOption('eventType', data.eventType);
    await this.selectAutocompleteOption('eventSubtype', data.eventSubtype);
    await selectAsset(this.page, '[data-cy=asset]', data.asset, data.assetId);
    await this.page.locator('[data-cy=amount] input').clear();
    await this.page.locator('[data-cy=amount] input').fill(data.amount);
    await this.page.locator('[data-cy=notes] textarea:not([aria-hidden])').fill(data.notes);
  }

  async fillEvmSwapEventForm(data: EvmSwapEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.selectLocation('ethereum');
    await this.page.locator('[data-cy=tx-ref] input').fill(data.txRef);
    await selectAsset(this.page, '[data-cy=spend-asset]', data.spendAsset, data.spendAssetId);
    await this.page.locator('[data-cy=spend-amount] input').clear();
    await this.page.locator('[data-cy=spend-amount] input').fill(data.spendAmount);
    await selectAsset(this.page, '[data-cy=receive-asset]', data.receiveAsset, data.receiveAssetId);
    await this.page.locator('[data-cy=receive-amount] input').clear();
    await this.page.locator('[data-cy=receive-amount] input').fill(data.receiveAmount);
  }

  private async selectNthAsset(
    dataCy: string,
    index: number,
    value: string,
    id?: string,
  ): Promise<void> {
    const container = this.page.locator(`[data-cy=${dataCy}]`).nth(index);
    await container.locator('[data-id=activator]').click();
    await container.locator('input').fill(value);
    const identifier = getValidSelectorFromEvmAddress((id ?? value).toLocaleLowerCase());
    await this.page.locator(`#asset-${identifier}`).click();
  }

  private async fillSubEventList(
    type: 'spend' | 'receive' | 'fee',
    items: { asset: string; assetId?: string; amount: string }[],
  ): Promise<void> {
    for (const [i, item] of items.entries()) {
      if (i > 0)
        await this.page.locator(`[data-cy=${type}-add]`).click();

      await this.selectNthAsset(`${type}-asset`, i, item.asset, item.assetId);
      await this.page.locator(`[data-cy=${type}-amount] input`).nth(i).clear();
      await this.page.locator(`[data-cy=${type}-amount] input`).nth(i).fill(item.amount);
    }
  }

  async fillEvmMultiSwapEventForm(data: EvmMultiSwapEventFixture): Promise<void> {
    await this.fillDatetime();
    await this.selectLocation('ethereum');
    await this.page.locator('[data-cy=tx-ref] input').fill(data.txRef);

    await this.fillSubEventList('spend', data.spend);
    await this.fillSubEventList('receive', data.receive);

    if (data.fees.length > 0) {
      await this.page.locator('[data-cy=has-fee]').click();
      await this.fillSubEventList('fee', data.fees);
    }
  }
}
