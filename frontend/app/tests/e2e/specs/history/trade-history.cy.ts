import type { ExternalTrade } from '../../support/types';
import { TradeHistoryPage } from '../../pages/history-page/trade-history-page';
import { RotkiApp } from '../../pages/rotki-app';
import { createUser } from '../../utils/user';

describe('trade history', () => {
  let username: string;
  let app: RotkiApp;
  let tradeHistoryPage: TradeHistoryPage;
  let externalTrades: ExternalTrade[];

  before(() => {
    app = new RotkiApp();
    tradeHistoryPage = new TradeHistoryPage();
    cy.fixture('history/trades.json').then((trade) => {
      externalTrades = trade;
    });
  });

  describe('manage data', () => {
    before(() => {
      username = createUser();
      app.fasterLogin(username);
      tradeHistoryPage.visit();
    });

    it('add two external trades', () => {
      // add trade by input rate
      tradeHistoryPage.addTrade(externalTrades[0]);
      tradeHistoryPage.visibleEntries(1);
      // add trade by input quote amount
      tradeHistoryPage.visit();
      tradeHistoryPage.addTrade(externalTrades[1]);
      tradeHistoryPage.visibleEntries(2);
      tradeHistoryPage.tradeIsVisible(0, externalTrades[0]);
      tradeHistoryPage.tradeIsVisible(1, externalTrades[1]);
    });

    it('edit external trade', () => {
      tradeHistoryPage.visibleEntries(2);
      tradeHistoryPage.tradeIsVisible(0, externalTrades[0]);
      tradeHistoryPage.editTrade(0, '123.2');
      tradeHistoryPage.tradeIsVisible(0, {
        ...externalTrades[0],
        amount: '123.2',
      });
    });

    it('delete external trade', () => {
      tradeHistoryPage.visibleEntries(2);
      tradeHistoryPage.tradeIsVisible(0, {
        ...externalTrades[0],
        amount: '123.2',
      });
      tradeHistoryPage.deleteTrade(0);
      tradeHistoryPage.confirmDelete();
      tradeHistoryPage.visibleEntries(1);
      tradeHistoryPage.tradeIsVisible(0, externalTrades[1]);
    });
  });

  it('filter and pagination', () => {
    username = createUser();
    app.fasterLogin(username);
    for (let i = 0; i < 6; i++) {
      const time = `08/10/2015 10:50:5${i}`;
      cy.addExternalTrade({
        ...externalTrades[0],
        time,
      });
      cy.addExternalTrade({
        ...externalTrades[1],
        time,
      });
    }

    for (let i = 0; i < 6; i++) {
      const time = `09/10/2015 10:50:5${i}`;
      cy.addExternalTrade({ ...externalTrades[0], location: 'equities', time });
      cy.addExternalTrade({ ...externalTrades[1], location: 'equities', time });
    }

    tradeHistoryPage.visit();

    // after addition, should have 24 entries on table
    tradeHistoryPage.visibleEntries(10);
    tradeHistoryPage.totalEntries(24);
    tradeHistoryPage.shouldBeOnPage('1 - 10');
    app.shouldNotHaveQueryParam('page');

    // go to page 2
    tradeHistoryPage.nextPage();
    tradeHistoryPage.shouldBeOnPage('11 - 20');
    app.shouldHaveQueryParam('page', '2');
    app.shouldNotHaveQueryParam('sort');

    // apply filter location
    tradeHistoryPage.filterTrades('location: equities');
    tradeHistoryPage.visibleEntries(10);
    tradeHistoryPage.totalEntries(12);
    tradeHistoryPage.shouldBeOnPage('1 - 10');
    app.shouldNotHaveQueryParam('page');

    // go to page 2
    tradeHistoryPage.nextPage();
    tradeHistoryPage.shouldBeOnPage('11 - 12');
    tradeHistoryPage.visibleEntries(2);
    app.shouldHaveQueryParam('page', '2');

    // history back, should go back to page 1
    cy.go(-1);
    tradeHistoryPage.shouldBeOnPage('1 - 10');
    tradeHistoryPage.visibleEntries(10);
    app.shouldNotHaveQueryParam('page');

    // history back, should remove filter
    cy.go(-1);
    tradeHistoryPage.totalEntries(24);
    tradeHistoryPage.shouldBeOnPage('1 - 10');

    // history forward, should reapply location filter
    cy.go(1);
    tradeHistoryPage.totalEntries(12);
    app.shouldNotHaveQueryParam('page');

    tradeHistoryPage.sortByColumn(4);
    app.shouldHaveQueryParam('sort', 'amount');
    app.shouldHaveQueryParam('sortOrder', 'asc');

    app.logout();
  });
});
