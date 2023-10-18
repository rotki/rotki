import { type ExternalTrade } from '../../support/types';
import { selectAsset } from '../../support/utils';
import { HistoryPage } from './index';

export class TradeHistoryPage {
  page = new HistoryPage();
  visit() {
    this.page.visit('history-trades');
  }

  createWaitForTrades() {
    cy.intercept({
      method: 'GET',
      url: '/api/1/trades**'
    }).as('apiCall');

    return () => {
      // Wait for response.status to be 200
      cy.wait('@apiCall', { timeout: 30000 })
        .its('response.statusCode')
        .should('equal', 200);
    };
  }

  addTrade(trade: ExternalTrade) {
    cy.get('[data-cy=closed-trades__add-trade]').click();
    cy.get('[data-cy=trade-form]').should('be.visible');
    cy.get('[data-cy=date]').type(`{selectall}{backspace}${trade.time}`);
    // clicking outside to a fully visible element to close the datepicker
    cy.get('[data-cy=bottom-dialog]').find('.v-card__title').click();

    cy.intercept({
      method: 'GET',
      url: '/api/1/tasks/*'
    }).as('priceTask');

    selectAsset('[data-cy=base-asset]', trade.base, trade.base_id);
    selectAsset('[data-cy=quote-asset]', trade.quote, trade.quote_id);
    cy.get(`[data-cy=type] input[value=${trade.trade_type}]`)
      .parentsUntil('.v-radio')
      .first()
      .click();
    cy.get('[data-cy=amount] input').type(trade.amount);
    cy.wait('@priceTask')
      .its('response.statusCode', { timeout: 10000 })
      .should('equal', 200);
    cy.get('[data-cy=trade-rate] [data-cy=primary]')
      .parent()
      .parent()
      .find('.v-progress-linear')
      .should('not.exist');
    if (trade.quote_amount) {
      cy.get('[data-cy=grouped-amount-input__swap-button]').click();
      cy.get('[data-cy=trade-rate] [data-cy=secondary] input').type(
        `{selectall}{backspace}${trade.quote_amount}`
      );
      cy.get('[data-cy=trade-rate] [data-cy=primary] input').should(
        'have.value',
        trade.rate
      );
    } else {
      cy.get('[data-cy=trade-rate] [data-cy=primary] input').type(
        `{selectall}{backspace}${trade.rate}`
      );
    }
    cy.get('[data-cy=fee] input').type(trade.fee);
    selectAsset('[data-cy=fee-currency]', trade.fee_currency, trade.fee_id);
    cy.get('[data-cy=link]').type(trade.link);
    cy.get('[data-cy=notes]').type(trade.notes);
    const waitForTrades = this.createWaitForTrades();
    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').click();
    waitForTrades();
    cy.get('[data-cy=trade-form]').should('not.exist');
    cy.get('[data-cy=bottom-dialog]').should('not.be.visible');
  }

  visibleEntries(visible: number) {
    cy.get('.v-data-table__progress').should('not.exist');
    cy.get('.v-data-table__empty-wrapper').should('not.exist');
    cy.get('[data-cy=closed-trades] tbody')
      .find('tr')
      .should('have.length', visible);
  }

  totalEntries(total: number) {
    cy.get('.v-data-table__progress').should('not.exist');
    cy.get('.v-data-table__empty-wrapper').should('not.exist');
    cy.get(
      '[data-cy=closed-trades] .v-data-footer:first-child .v-data-footer__pagination .items-page-select span:last-child'
    ).should('contain.text', total);
  }

  tradeIsVisible(position: number, trade: ExternalTrade) {
    cy.get('[data-cy=closed-trades] tbody > tr').eq(position).as('row');

    cy.get('@row')
      .find('td')
      .eq(3)
      .should('contain', trade.trade_type.toLowerCase());

    cy.get('@row')
      .find('td')
      .eq(4)
      .find('[data-cy=display-amount]')
      .should('contain', trade.amount);

    cy.get('@row')
      .find('td')
      .eq(5)
      .find('[data-cy=trade-base]')
      .find('[data-cy=details-symbol]')
      .should('contain', trade.base);

    cy.get('@row')
      .find('td')
      .eq(7)
      .find('[data-cy=trade-quote]')
      .find('[data-cy=details-symbol]')
      .should('contain', trade.quote);
  }

  editTrade(position: number, amount: string) {
    cy.get('[data-cy=closed-trades] tbody > tr')
      .eq(position)
      .find('[data-cy=row-edit]')
      .click();

    cy.get('[data-cy=trade-form]').should('be.visible');
    cy.get('[data-cy=amount] input').clear();
    cy.get('[data-cy=amount] input').type(amount);

    const waitForTrades = this.createWaitForTrades();
    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').click();
    waitForTrades();
    cy.get('[data-cy=trade-form]').should('not.exist');
    cy.get('.v-progress-linear__buffer').should('not.exist');
  }

  deleteTrade(position: number) {
    cy.get('[data-cy=closed-trades] tbody > tr')
      .eq(position)
      .find('[data-cy=row-delete]')
      .click();
  }

  confirmDelete() {
    cy.get('[data-cy=confirm-dialog]')
      .find('[data-cy=dialog-title]')
      .should('contain', 'Delete Trade');
    const waitForTrades = this.createWaitForTrades();
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
    waitForTrades();
    cy.get('[data-cy=confirm-dialog]').should('not.be.exist');
  }

  filterTrades(filter: string) {
    cy.get('[data-cy="table-filter"]').scrollIntoView();
    cy.get('[data-cy="table-filter"]').should('be.visible');
    cy.get('[data-cy="table-filter"]').type(`${filter}{enter}{esc}`);
  }

  nextPage() {
    cy.get(
      '[data-cy=closed-trades] .v-data-footer:first-child .v-data-footer__icons-after button:first-child'
    ).click();
  }

  shouldBeOnPage(page: number) {
    cy.get('.v-data-table__progress').should('not.exist');
    cy.get('.v-data-table__empty-wrapper').should('not.exist');
    cy.get(
      '[data-cy=closed-trades] .v-data-footer:first-child .v-data-footer__pagination .items-page-select div .v-select__slot > input'
    ).should('have.value', page);
  }
}
