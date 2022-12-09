import { Guid } from '../../../common/guid';
import { HistoryPage } from '../../pages/history-page';
import { TradeHistoryPage } from '../../pages/history-page/trade-history-page';
import { RotkiApp } from '../../pages/rotki-app';
import { type ExternalTrade } from '../../support/types';

describe(
  'trade history',
  {
    retries: {
      runMode: 2,
      openMode: 0
    }
  },
  () => {
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
  }
);
