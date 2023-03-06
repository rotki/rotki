import { type ExternalLedgerAction } from '../../support/types';
import { selectAsset, selectLocation } from '../../support/utils';

export class LedgerActionPage {
  visit() {
    cy.get('.history__ledger-actions')
      .scrollIntoView()
      .should('be.visible')
      .click();
  }

  createWaitForLedgerActions() {
    cy.intercept({
      method: 'GET',
      url: '/api/1/ledgeractions**'
    }).as('apiCall');

    return () => {
      // Wait for response.status to be 200
      cy.wait('@apiCall', { timeout: 30000 })
        .its('response.statusCode')
        .should('equal', 200);
    };
  }

  addLedgerAction(ledgerAction: ExternalLedgerAction) {
    cy.get('[data-cy=ledger-actions__add]').click();
    cy.get('[data-cy=ledger-action-form]').should('be.visible');
    selectLocation('[data-cy=location]', ledgerAction.location);
    cy.get('[data-cy=datetime]').type(
      `{selectall}{backspace}${ledgerAction.datetime}`
    );

    // clicking outside to a fully visible element to close the datepicker
    cy.get('[data-cy=bottom-dialog]').find('.card-title').click();

    selectAsset('[data-cy=asset]', ledgerAction.asset, ledgerAction.asset_id);
    cy.get('[data-cy=amount] input').type(ledgerAction.amount);
    cy.get('[data-cy=action-type]').parent().click();
    cy.get('.v-menu__content').contains(ledgerAction.action_type).click();
    cy.get('[data-cy=rate] input').type(`${ledgerAction.rate}`);
    selectAsset(
      '[data-cy=rate-asset]',
      ledgerAction.rate_asset,
      ledgerAction.rate_asset_id
    );
    cy.get('[data-cy=link]').type(ledgerAction.link);
    cy.get('[data-cy=notes]').type(ledgerAction.notes);
    const waitForLedgerActions = this.createWaitForLedgerActions();
    cy.get('.big-dialog__buttons__confirm').click();
    waitForLedgerActions();
    cy.get('[data-cy=ledger-action-form]').should('not.exist');
  }

  visibleEntries(visible: number) {
    cy.get('[data-cy=ledger-actions] tbody').should('be.visible');
    cy.get('.v-data-table__progress').should('not.exist');
    cy.get('.v-data-table__empty-wrapper').should('not.exist');
    cy.get('[data-cy=ledger-actions] tbody')
      .find('tr')
      .should('have.length', visible);
  }

  totalEntries(total: number) {
    cy.get('.v-data-table__progress').should('not.exist');
    cy.get('.v-data-table__empty-wrapper').should('not.exist');
    cy.get(
      '[data-cy=ledger-actions] .v-data-footer:first-child .v-data-footer__pagination .items-page-select span:last-child'
    ).should('contain.text', total);
  }

  ledgerActionIsVisible(position: number, ledgerAction: ExternalLedgerAction) {
    cy.get('[data-cy=ledger-actions] tbody > tr').eq(position).as('row');

    cy.get('@row')
      .find('td')
      .eq(2)
      .find('[data-cy=ledger-action-location]')
      .should('contain', ledgerAction.location);

    cy.get('@row')
      .find('td')
      .eq(3)
      .find('[data-cy=ledger-action-type]')
      .should('contain', ledgerAction.action_type.toLowerCase());

    cy.get('@row')
      .find('td')
      .eq(4)
      .find('[data-cy=ledger-action-asset]')
      .find('[data-cy=details-symbol]')
      .should('contain', ledgerAction.asset);

    cy.get('@row')
      .find('td')
      .eq(5)
      .find('[data-cy=display-amount]')
      .should('contain', ledgerAction.amount);
  }

  editTrade(position: number, amount: string) {
    cy.get('[data-cy=ledger-actions] tbody > tr')
      .eq(position)
      .find('[data-cy=row-edit]')
      .click();

    cy.get('[data-cy=ledger-action-form]').should('be.visible');
    cy.get('[data-cy=amount] input').clear();
    cy.get('[data-cy=amount] input').type(amount);

    const waitForLedgerActions = this.createWaitForLedgerActions();
    cy.get('.big-dialog__buttons__confirm').click();
    waitForLedgerActions();
    cy.get('[data-cy=ledger-action-form]').should('not.exist');
  }

  deleteLedgerAction(position: number) {
    cy.get('[data-cy=ledger-actions] tbody > tr')
      .eq(position)
      .find('[data-cy=row-delete]')
      .click();
  }

  confirmDelete() {
    cy.get('[data-cy=confirm-dialog]')
      .find('[data-cy=dialog-title]')
      .should('contain', 'Delete Ledger Action');
    const waitForLedgerActions = this.createWaitForLedgerActions();
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
    waitForLedgerActions();
    cy.get('[data-cy=confirm-dialog]').should('not.be.exist');
  }

  filterLedgerActions(filter: string) {
    cy.get('[data-cy="table-filter"]')
      .scrollIntoView()
      .should('be.visible')
      .type(`${filter}{enter}`);
  }

  nextPage() {
    cy.get(
      '[data-cy=ledger-actions] .v-data-footer:first-child .v-data-footer__icons-after button:first-child'
    ).click();
  }

  shouldBeOnPage(page: number) {
    cy.get('.v-data-table__progress').should('not.exist');
    cy.get('.v-data-table__empty-wrapper').should('not.exist');
    cy.get(
      '[data-cy=ledger-actions] .v-data-footer:first-child .v-data-footer__pagination .items-page-select div .v-select__slot > input'
    ).should('have.value', page);
  }
}
