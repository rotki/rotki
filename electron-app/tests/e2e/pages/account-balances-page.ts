import { ApiManualBalance } from '../../../src/services/types-api';
import { bigNumberify } from '../../../src/utils/bignumbers';

export class AccountBalancesPage {
  visit() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__accounts-balances').click();
  }

  addBalance(balances: ApiManualBalance) {
    cy.get('.manual-balances-form__asset').type(balances.asset);
    cy.get(`#asset-${balances.asset.toLocaleLowerCase()}`).click();
    cy.get('.manual-balances-form__label').type(balances.label);
    cy.get('.manual-balances-form__amount').type(balances.amount);
    for (const tag of balances.tags) {
      cy.get('.manual-balances-form__tags').type(tag).type('{enter}');
    }
    cy.get('.manual-balances-form__location').click();
    cy.get(`#balance-location__${balances.location}`).click();
    cy.get('.manual-balances-form__save').click();
  }

  visibleEntries(visible: number) {
    cy.get('.manual-balances-list tbody')
      .find('tr')
      .should('have.length', visible);
  }

  isVisible(position: number, balance: ApiManualBalance) {
    cy.get('.manual-balances-list tbody').find('tr').eq(position).as('row');

    cy.get('@row')
      .find('.manual-balances-list__label')
      .should('contain', balance.label);

    cy.get('@row')
      .find('.manual-balances-list__amount')
      .should('contain', bigNumberify(balance.amount).toFormat(2));

    cy.get('@row')
      .find('.manual-balances-list__location')
      .should('contain', balance.location);

    cy.get('@row')
      .find('.asset-details__details__symbol')
      .should('contain', balance.asset);

    for (const tag of balance.tags) {
      cy.get('@row').find('.tag').contains(tag).should('be.visible');
    }
  }

  editBalance(position: number, amount: string) {
    cy.get('.manual-balances-list tbody')
      .find('tr')
      .eq(position)
      .find('button.manual-balances-list__actions__edit')
      .click();

    cy.get('.manual-balances-list__edit-form').as('edit-form');
    cy.get('@edit-form').find('.manual-balances-form__amount input').clear();
    cy.get('@edit-form').find('.manual-balances-form__amount').type(amount);
    cy.get('@edit-form').find('.manual-balances-form__save').click();
  }

  deleteBalance(position: number) {
    cy.get('.manual-balances-list tbody')
      .find('tr')
      .eq(position)
      .find('.manual-balances-list__actions__delete')
      .click();
  }

  confirmDelete() {
    cy.get('.confirm-dialog__title').should(
      'contain',
      'Delete manually tracked balance'
    );
    cy.get('.confirm-dialog__buttons__confirm').click();
  }

  showsCurrency(currency: string) {
    cy.get('.manual-balances-list')
      .contains(`${currency} Value`)
      .should('be.visible');
  }
}
