import type { ExternalTrade } from '../../support/types';
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
      url: '/api/1/trades**',
    }).as('apiCall');

    return () => {
      // Wait for response.status to be 200
      cy.wait('@apiCall', { timeout: 30000 }).its('response.statusCode').should('equal', 200);
    };
  }

  addTrade(trade: ExternalTrade) {
    cy.get('[data-cy=closed-trades__add-trade]').click();
    cy.get('[data-cy=trade-form]').should('be.visible');
    cy.get('[data-cy=date]').type(`{selectall}{backspace}${trade.time}`);
    // clicking outside to a fully visible element to close the datepicker
    cy.get('[data-cy=bottom-dialog] h5').click();

    cy.intercept({
      method: 'GET',
      url: '/api/1/tasks/*',
    }).as('priceTask');

    cy.get(`[data-cy=trade-input-${trade.trade_type}] input`).click();
    selectAsset('[data-cy=base-asset]', trade.base, trade.base_id);
    selectAsset('[data-cy=quote-asset]', trade.quote, trade.quote_id);
    cy.get('[data-cy=amount] input').type(trade.amount);
    cy.wait('@priceTask').its('response.statusCode', { timeout: 10000 }).should('equal', 200);
    cy.get('[data-cy=trade-rate] [data-cy=primary]')
      .parent()
      .parent()
      .find('[role=progressbar]')
      .should('not.be.visible');
    if (trade.quote_amount) {
      cy.get('[data-cy=grouped-amount-input__swap-button]').click();
      cy.get('[data-cy=trade-rate] [data-cy=secondary] input').type(`{selectall}{backspace}${trade.quote_amount}`);
      cy.get('[data-cy=trade-rate] [data-cy=primary] input').should('have.value', trade.rate);
    }
    else {
      cy.get('[data-cy=trade-rate] [data-cy=primary] input').type(`{selectall}{backspace}${trade.rate}`);
    }
    cy.get('[data-cy=fee] input').type(trade.fee);
    selectAsset('[data-cy=fee-currency]', trade.fee_currency, trade.fee_id);
    cy.get('[data-cy=link]').type(trade.link);
    cy.get('[data-cy=notes] textarea:not([aria-hidden="true])').type(trade.notes);
    const waitForTrades = this.createWaitForTrades();
    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').click();
    waitForTrades();
    cy.get('[data-cy=trade-form]').should('not.exist');
    cy.get('[data-cy=bottom-dialog]').should('not.exist');
  }

  visibleEntries(visible: number) {
    cy.get('[class*=_thead__loader_] div[role=progressbar][class*=_progress_]').should('not.exist');
    cy.get('[class*=_tbody__loader_] div[role=progressbar][class*=_circular_]').should('not.exist');
    cy.get('[data-cy=closed-trades] tbody').find('tr').should('have.length', visible);
  }

  totalEntries(total: number) {
    cy.get('[class*=_thead__loader_] div[role=progressbar][class*=_progress_]').should('not.exist');
    cy.get('[class*=_tbody__loader_] div[role=progressbar][class*=_circular_]').should('not.exist');
    cy.get('[data-cy=closed-trades] [data-cy=table-pagination] span[class*=_indicator_]').should('contain.text', total);
  }

  tradeIsVisible(position: number, trade: ExternalTrade) {
    cy.get('[data-cy=closed-trades] tbody > tr').eq(position).as('row');

    cy.get('@row').find('td').eq(3).should('contain', trade.trade_type.toLowerCase());

    cy.get('@row').find('td').eq(4).find('[data-cy=display-amount]').should('contain', trade.amount);

    cy.get('@row')
      .find('td')
      .eq(5)
      .find('[data-cy=trade-base]')
      .find('[data-cy=list-title]')
      .should('contain', trade.base);

    cy.get('@row')
      .find('td')
      .eq(8)
      .find('[data-cy=trade-quote]')
      .find('[data-cy=list-title]')
      .should('contain', trade.quote);
  }

  editTrade(position: number, amount: string) {
    cy.get('[data-cy=closed-trades] tbody > tr').eq(position).find('[data-cy=row-edit]').click();

    cy.get('[data-cy=trade-form]').should('be.visible');
    cy.get('[data-cy=amount] input').clear();
    cy.get('[data-cy=amount] input').type(amount);

    const waitForTrades = this.createWaitForTrades();
    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').click();
    waitForTrades();
    cy.get('[data-cy=trade-form]').should('not.exist');
    cy.get('.notification-indicator-progress').should('not.exist');
  }

  deleteTrade(position: number) {
    cy.get('[data-cy=closed-trades] tbody > tr').eq(position).find('[data-cy=row-delete]').click();
  }

  confirmDelete() {
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=dialog-title]').should('contain', 'Delete Trade');
    const waitForTrades = this.createWaitForTrades();
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
    waitForTrades();
    cy.get('[data-cy=confirm-dialog]').should('not.exist');
  }

  filterTrades(filter: string) {
    cy.get('[data-cy=table-filter]').scrollIntoView();
    cy.get('[data-cy=table-filter] [data-id=activator] > span:last-child').click();
    cy.get('[data-cy=table-filter] input').type(`${filter}`);
    cy.get('div[role="menu-content"] button:first-child').click();
  }

  nextPage() {
    cy.get('[data-cy=closed-trades] [data-cy=table-pagination] [class*=_navigation_] button:nth-child(3)')
      .first()
      .click();
  }

  shouldBeOnPage(range: string) {
    cy.get('[class*=_thead__loader_] div[role=progressbar][class*=_progress_]').should('not.exist');
    cy.get('[class*=_tbody__loader_] div[role=progressbar][class*=_circular_]').should('not.exist');
    cy.get('[data-cy=closed-trades] [data-cy=table-pagination] [class*=_ranges_] [data-id=activator]').should(
      'contain',
      range,
    );
  }

  sortByColumn(number: number) {
    cy.get('[data-cy=closed-trades] thead th').eq(number).click();
  }
}
