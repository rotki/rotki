import { ExternalTrade } from '../support/types';
import { selectAsset } from '../support/utils';

export class HistoryPage {
  visit() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__history').click();
    cy.get('.navigation__history-trades').click();
  }

  addTrade(externalTrade: ExternalTrade) {
    cy.get('.closed-trades__add-trade').click();
    cy.get('.big-dialog').should('be.visible');
    cy.get('[data-cy=date]')
      .type(`{selectall}{backspace}${externalTrade.time}`)
      .click(); // Click is needed to hide the popup

    const [base, quote] = externalTrade.pair.split('_');
    selectAsset('[data-cy=base_asset]', base);
    selectAsset('[data-cy=quote_asset]', quote);
    cy.get('[data-cy=type] input').check(externalTrade.trade_type, {
      force: true
    });
    cy.get('[data-cy=amount]').type(externalTrade.amount);
    cy.get('[data-cy=rate]').type(
      `{selectall}{backspace}${externalTrade.rate}`
    );
    cy.get('[data-cy=fee]').type(externalTrade.fee);
    selectAsset('[data-cy=fee-currency]', externalTrade.fee_currency);
    cy.get('[data-cy=link]').type(externalTrade.link);
    cy.get('[data-cy=notes]').type(externalTrade.notes);
    cy.get('.big-dialog__buttons__confirm').click();
    cy.get('.big-dialog').should('not.be.visible');
  }

  confirmDelete() {
    cy.get('.confirm-dialog__title').should('contain', 'Delete Trade');
    cy.get('.confirm-dialog__buttons__confirm').click();
    cy.get('.confirm-dialog__title').should('not.be.visible');
  }

  visibleEntries(visible: number) {
    cy.get('.closed-trades tbody').find('tr').should('have.length', visible);
  }

  tradeIsVisible(position: number, otcTrade: ExternalTrade) {
    cy.get('.closed-trades tbody > tr').eq(position).as('row');

    cy.get('@row').find('td').eq(3).should('contain', otcTrade.pair);
    cy.get('@row')
      .find('td')
      .eq(5)
      .find('.amount-display__value')
      .should('contain', otcTrade.amount);
    cy.get('@row').find('td').eq(2).should('contain', otcTrade.trade_type);
  }

  editTrade(position: number, amount: string) {
    cy.get('.closed-trades tbody > tr')
      .eq(position)
      .find('button.closed-trades__trade__actions__edit')
      .click();

    cy.get('.big-dialog').should('be.visible');
    cy.get('[data-cy=amount]').clear();
    cy.get('[data-cy=amount]').type(amount);

    cy.get('.big-dialog__buttons__confirm').click();
    cy.get('.big-dialog').should('not.be.visible');
  }

  deleteTrade(position: number) {
    cy.get('.closed-trades tbody > tr')
      .eq(position)
      .find('.closed-trades__trade__actions__delete')
      .click();
  }
}
