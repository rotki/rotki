import { OTCTrade } from '../support/types';

export class OtcPage {
  visit() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__otc-trades').click();
  }

  addTrade(otcData: OTCTrade) {
    cy.get('.otc-form__date').type(otcData.time).click(); // Click is needed to hide the popup
    cy.get('.otc-form__pair').type(otcData.pair);
    cy.get('.otc-form__type input').check(otcData.trade_type, { force: true });
    cy.get('.otc-form__amount').type(otcData.amount);
    cy.get('.otc-form__rate').type(otcData.rate);
    cy.get('.otc-form__fee').type(otcData.fee);
    cy.get('.otc-form__fee-currency').type(otcData.fee_currency);
    cy.get('.otc-form__link').type(otcData.link);
    cy.get('.otc-form__notes').type(otcData.notes);
    cy.get('.otc-form__buttons__save').click();
  }

  confirmSuccess() {
    cy.get('.message-dialog__title').should('contain', 'Success');
    cy.get('.message-dialog__buttons__confirm').click();
  }

  confirmDelete() {
    cy.get('.confirm-dialog__title').should('contain', 'Delete OTC Trade');
    cy.get('.confirm-dialog__buttons__confirm').click();
    cy.get('.confirm-dialog__title').should('not.be.visible');
  }

  visibleEntries(visible: number) {
    cy.get('.otc-trades tbody').find('tr').should('have.length', visible);
  }

  tradeIsVisible(position: number, otcTrade: OTCTrade) {
    cy.get('.otc-trades tbody > tr').eq(position).as('row');

    cy.get('@row')
      .find('.otc-trades__trade__pair')
      .should('contain', otcTrade.pair);

    cy.get('@row')
      .find('.otc-trades__trade__amount')
      .should('contain', otcTrade.amount);

    cy.get('@row')
      .find('.otc-trades__trade__type')
      .should('contain', otcTrade.trade_type);
  }

  editTrade(position: number, amount: string) {
    cy.get('.otc-trades tbody > tr')
      .eq(position)
      .find('button.otc-trades__trade__actions__edit')
      .click();

    cy.get('.otc-form__amount input').clear();
    cy.get('.otc-form__amount').type(amount);

    cy.get('.otc-form__buttons__save').click();
  }

  deleteTrade(position: number) {
    cy.get('.otc-trades tbody > tr')
      .eq(position)
      .find('.otc-trades__trade__actions__delete')
      .click();
  }
}
