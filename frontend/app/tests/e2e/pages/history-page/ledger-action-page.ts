import { ExternalLedgerAction } from '../../support/types';
import { selectAsset, selectLocation } from '../../support/utils';

export class LedgerActionPage {
  visit() {
    cy.get('.history__ledger-actions')
      .scrollIntoView()
      .should('be.visible')
      .click({
        force: true
      });
  }

  fetchLedgerActions() {
    cy.intercept({
      method: 'GET',
      url: '/api/1/ledgeractions**'
    }).as('apiCall');

    return () => {
      // Wait for response.status to be 200
      cy.wait('@apiCall').its('response.statusCode').should('equal', 200);
      cy.wait(500);
    };
  }

  addLedgerAction(ledgerAction: ExternalLedgerAction) {
    cy.get('.ledger-actions__add').click();
    cy.get('[data-cy=ledger-action-form]').should('be.visible');
    selectLocation('[data-cy=location]', ledgerAction.location);
    cy.get('[data-cy=datetime]')
      .type(`{selectall}{backspace}${ledgerAction.datetime}`)
      .click({ force: true }); // Click is needed to hide the popup
    selectAsset('[data-cy=asset]', ledgerAction.asset, ledgerAction.asset_id);
    cy.get('[data-cy=amount]').type(ledgerAction.amount);
    cy.get('[data-cy=action-type]').parent().click();
    cy.get('.v-menu__content').contains(ledgerAction.action_type).click();
    cy.get('[data-cy=rate]').type(`${ledgerAction.rate}`);
    selectAsset(
      '[data-cy=rate-asset]',
      ledgerAction.rate_asset,
      ledgerAction.rate_asset_id
    );
    cy.get('[data-cy=link]').type(ledgerAction.link);
    cy.get('[data-cy=notes]').type(ledgerAction.notes);
    const fetchLedgerActionsAssertion = this.fetchLedgerActions();
    cy.get('.big-dialog__buttons__confirm').click();
    fetchLedgerActionsAssertion();
    cy.get('[data-cy=ledger-action-form]').should('not.exist');
  }

  visibleEntries(visible: number) {
    cy.get('.ledger_actions tbody').find('tr').should('have.length', visible);
  }

  ledgerActionIsVisible(position: number, ledgerAction: ExternalLedgerAction) {
    cy.get('.ledger_actions tbody > tr').eq(position).as('row');

    cy.get('@row')
      .find('td')
      .eq(1)
      .find('[data-cy=ledger-action-location]')
      .should('contain', ledgerAction.location);

    cy.get('@row')
      .find('td')
      .eq(2)
      .find('[data-cy=ledger-action-type]')
      .should('contain', ledgerAction.action_type);

    cy.get('@row')
      .find('td')
      .eq(3)
      .find('[data-cy=ledger-action-asset]')
      .find('[data-cy=details-symbol]')
      .should('contain', ledgerAction.asset);

    cy.get('@row')
      .find('td')
      .eq(4)
      .find('[data-cy=display-amount]')
      .should('contain', ledgerAction.amount);
  }

  editTrade(position: number, amount: string) {
    cy.get('.ledger_actions tbody > tr')
      .eq(position)
      .find('[data-cy=row-edit]')
      .click({ force: true });

    cy.get('[data-cy=ledger-action-form]').should('be.visible');
    cy.get('[data-cy=amount]').clear();
    cy.get('[data-cy=amount]').type(amount);

    const fetchLedgerActionsAssertion = this.fetchLedgerActions();
    cy.get('.big-dialog__buttons__confirm').click();
    fetchLedgerActionsAssertion();
    cy.get('[data-cy=ledger-action-form]').should('not.exist');
  }

  deleteLedgerAction(position: number) {
    cy.get('.ledger_actions tbody > tr')
      .eq(position)
      .find('[data-cy=row-delete]')
      .click();
  }

  confirmDelete() {
    cy.get('[data-cy=confirm-dialog]')
      .find('[data-cy=dialog-title]')
      .should('contain', 'Delete Ledger Action');
    const fetchLedgerActionsAssertion = this.fetchLedgerActions();
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
    fetchLedgerActionsAssertion();
    cy.get('[data-cy=confirm-dialog]').should('not.be.exist');
  }
}
