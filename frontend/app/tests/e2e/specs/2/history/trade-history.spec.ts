import { Guid } from '../../../common/guid';
import { HistoryPage } from '../../../pages/history-page';
import { TradeHistoryPage } from '../../../pages/history-page/trade-history-page';
import { RotkiApp } from '../../../pages/rotki-app';
import { type ExternalTrade } from '../../../support/types';

describe('trade history', () => {
  let username: string;
  let app: RotkiApp;
  let page: HistoryPage;
  let tradeHistoryPage: TradeHistoryPage;
  let externalTrades: ExternalTrade[];

  beforeEach(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new HistoryPage();
    tradeHistoryPage = new TradeHistoryPage();

    app.fasterLogin(username);
    cy.fixture('history/trades').then(trade => {
      externalTrades = trade;
    });
  });

  afterEach(() => {
    app.fasterLogout();
  });

  it('add two external trades', () => {
    page.visit();
    tradeHistoryPage.visit();
    // add trade by input rate
    tradeHistoryPage.addTrade(externalTrades[0]);
    // add trade by input quote amount
    tradeHistoryPage.addTrade(externalTrades[1]);
    tradeHistoryPage.visibleEntries(2);
    tradeHistoryPage.tradeIsVisible(0, externalTrades[0]);
    tradeHistoryPage.tradeIsVisible(1, externalTrades[1]);
  });

  it('edit external trade', () => {
    cy.addExternalTrade(externalTrades[0]);
    page.visit();
    tradeHistoryPage.visit();
    tradeHistoryPage.visibleEntries(1);
    tradeHistoryPage.tradeIsVisible(0, externalTrades[0]);
    tradeHistoryPage.editTrade(0, '123.2');
    tradeHistoryPage.tradeIsVisible(0, {
      ...externalTrades[0],
      amount: '123.2'
    });
  });

  it('delete external trade', () => {
    cy.addExternalTrade(externalTrades[0]);
    cy.addExternalTrade(externalTrades[1]);
    page.visit();
    tradeHistoryPage.visit();
    tradeHistoryPage.visibleEntries(2);
    tradeHistoryPage.tradeIsVisible(0, externalTrades[0]);
    tradeHistoryPage.deleteTrade(0);
    tradeHistoryPage.confirmDelete();
    tradeHistoryPage.visibleEntries(1);
    tradeHistoryPage.tradeIsVisible(0, externalTrades[1]);
  });

  it('filter and pagination', () => {
    for (let i = 0; i < 6; i++) {
      const time = `08/10/2015 10:50:5${i}`;
      cy.addExternalTrade({
        ...externalTrades[0],
        time
      });
      cy.addExternalTrade({
        ...externalTrades[1],
        time
      });
    }

    for (let i = 0; i < 6; i++) {
      const time = `09/10/2015 10:50:5${i}`;
      cy.addExternalTrade({ ...externalTrades[0], location: 'equities', time });
      cy.addExternalTrade({ ...externalTrades[1], location: 'equities', time });
    }

    page.visit();
    tradeHistoryPage.visit();

    // after addition, should have 24 entries on table
    tradeHistoryPage.visibleEntries(10);
    tradeHistoryPage.totalEntries(24);
    tradeHistoryPage.shouldBeOnPage(1);

    // go to page 2
    tradeHistoryPage.nextPage();
    tradeHistoryPage.shouldBeOnPage(2);

    // apply filter location
    tradeHistoryPage.filterTrades('location: equities');
    tradeHistoryPage.visibleEntries(10);
    tradeHistoryPage.totalEntries(12);
    tradeHistoryPage.shouldBeOnPage(1);

    // go to page 2
    tradeHistoryPage.nextPage();
    tradeHistoryPage.shouldBeOnPage(2);
    tradeHistoryPage.visibleEntries(2);

    // history back, should go back to page 1
    cy.go(-1);
    tradeHistoryPage.shouldBeOnPage(1);
    tradeHistoryPage.visibleEntries(10);

    // history back, should remove filter
    cy.go(-1);
    tradeHistoryPage.totalEntries(24);
    tradeHistoryPage.shouldBeOnPage(1);

    // history forward, should reapply location filter
    cy.go(1);
    tradeHistoryPage.totalEntries(12);
  });
});
