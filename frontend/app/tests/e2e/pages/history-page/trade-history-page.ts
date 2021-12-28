import { ExternalTrade } from '../../support/types';
import { selectAsset } from '../../support/utils';

export class TradeHistoryPage {
  visit() {
    cy.get('.history__trades').scrollIntoView().should('be.visible').click({
      force: true
    });
  }

  fetchTrades() {
    cy.intercept({
      method: 'GET',
      url: '/api/1/trades**'
    }).as('apiCall');

    return () => {
      // Wait for response.status to be 200
      cy.wait('@apiCall').its('response.statusCode').should('equal', 200);
      cy.wait(500);
    };
  }

  addTrade(trade: ExternalTrade) {
    cy.get('.closed-trades__add-trade').click();
    cy.get('[data-cy=trade-form]').should('be.visible');
    cy.get('[data-cy=date]')
      .type(`{selectall}{backspace}${trade.time}`)
      .click({ force: true }); // Click is needed to hide the popup

    selectAsset('[data-cy=base-asset]', trade.base, trade.base_id);
    selectAsset('[data-cy=quote-asset]', trade.quote, trade.quote_id);
    cy.get('[data-cy=type] input').check(trade.trade_type, {
      force: true
    });
    cy.get('[data-cy=amount]').type(trade.amount);
    cy.get('[data-cy=rate]')
      .parent()
      .parent()
      .find('.v-progress-linear')
      .should('not.exist');
    if (trade.quote_amount) {
      cy.get('[data-cy=grouped-amount-input__swap-button]').click();
      cy.get('[data-cy=quote-amount]').type(
        `{selectall}{backspace}${trade.quote_amount}`
      );
      cy.get('[data-cy=rate]').should('have.value', trade.rate);
    } else {
      cy.get('[data-cy=rate]').type(`{selectall}{backspace}${trade.rate}`);
    }
    cy.get('[data-cy=fee]').type(trade.fee);
    selectAsset('[data-cy=fee-currency]', trade.fee_currency, trade.fee_id);
    cy.get('[data-cy=link]').type(trade.link);
    cy.get('[data-cy=notes]').type(trade.notes);
    const fetchTradesAssertion = this.fetchTrades();
    cy.get('.big-dialog__buttons__confirm').click();
    fetchTradesAssertion();
    cy.get('[data-cy=trade-form]').should('not.exist');
  }

  visibleEntries(visible: number) {
    cy.get('.closed-trades tbody').find('tr').should('have.length', visible);
  }

  tradeIsVisible(position: number, trade: ExternalTrade) {
    cy.get('.closed-trades tbody > tr').eq(position).as('row');

    cy.get('@row').find('td').eq(2).should('contain', trade.trade_type);

    cy.get('@row')
      .find('td')
      .eq(3)
      .find('[data-cy=trade-base]')
      .find('[data-cy=details-symbol]')
      .should('contain', trade.base);

    cy.get('@row')
      .find('td')
      .eq(5)
      .find('[data-cy=trade-quote]')
      .find('[data-cy=details-symbol]')
      .should('contain', trade.quote);

    cy.get('@row')
      .find('td')
      .eq(7)
      .find('[data-cy=display-amount]')
      .should('contain', trade.amount);
  }

  editTrade(position: number, amount: string) {
    cy.get('.closed-trades tbody > tr')
      .eq(position)
      .find('[data-cy=row-edit]')
      .click({ force: true });

    cy.get('[data-cy=trade-form]').should('be.visible');
    cy.get('[data-cy=amount]').clear();
    cy.get('[data-cy=amount]').type(amount);

    const fetchTradesAssertion = this.fetchTrades();
    cy.get('.big-dialog__buttons__confirm').click();
    fetchTradesAssertion();
    cy.get('[data-cy=trade-form]').should('not.exist');
  }

  deleteTrade(position: number) {
    cy.get('.closed-trades tbody > tr')
      .eq(position)
      .find('[data-cy=row-delete]')
      .click();
  }

  confirmDelete() {
    cy.get('[data-cy=confirm-dialog]')
      .find('[data-cy=dialog-title]')
      .should('contain', 'Delete Trade');
    const fetchTradesAssertion = this.fetchTrades();
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
    fetchTradesAssertion();
    cy.get('[data-cy=confirm-dialog]').should('not.be.exist');
  }
}
