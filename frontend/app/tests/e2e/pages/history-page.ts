import { OTCTrade } from '../support/types';

export class HistoryPage {
  visit() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__history').click();
    cy.get('.navigation__history-trades').click();
  }

  addTrade(otcData: OTCTrade) {
    cy.get('.closed-trades__add-trade').click();
    cy.get('.otc-form__date')
      .type(`{selectall}{backspace}${otcData.time}`)
      .click(); // Click is needed to hide the popup
    cy.get('.otc-form__pair').type(otcData.pair);
    cy.get('.otc-form__type input').check(otcData.trade_type, { force: true });
    cy.get('.otc-form__amount').type(otcData.amount);
    cy.get('.otc-form__rate input').type(otcData.rate);
    cy.get('.otc-form__fee').type(otcData.fee);
    cy.get('.otc-form__fee-currency').type(otcData.fee_currency);
    cy.get(`#asset-${otcData.fee_currency.toLocaleLowerCase()}`).click();
    cy.get('.otc-form__link').type(otcData.link);
    cy.get('.otc-form__notes').type(otcData.notes);
    cy.get('.big-dialog__buttons__confirm').click();
  }

  confirmDelete() {
    cy.get('.confirm-dialog__title').should('contain', 'Delete Trade');
    cy.get('.confirm-dialog__buttons__confirm').click();
    cy.get('.confirm-dialog__title').should('not.be.visible');
  }

  visibleEntries(visible: number) {
    cy.get('.closed-trades tbody').find('tr').should('have.length', visible);
  }

  tradeIsVisible(position: number, otcTrade: OTCTrade) {
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

    cy.get('.otc-form__amount input').clear();
    cy.get('.otc-form__amount').type(amount);

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
