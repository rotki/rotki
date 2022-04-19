import { Guid } from '../../../common/guid';
import { HistoryPage } from '../../pages/history-page';
import { TradeHistoryPage } from '../../pages/history-page/trade-history-page';
import { RotkiApp } from '../../pages/rotki-app';
import { ExternalTrade } from '../../support/types';

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

    before(() => {
      username = Guid.newGuid().toString();
      app = new RotkiApp();
      page = new HistoryPage();
      tradeHistoryPage = new TradeHistoryPage();

      app.visit();
      app.createAccount(username);
      page.visit();
      cy.fixture('history/trades').then(trade => {
        externalTrades = trade;
      });
      tradeHistoryPage.visit();
    });

    after(() => {
      app.logout();
    });

    it('add two external trades', () => {
      // add trade by input rate
      tradeHistoryPage.addTrade(externalTrades[0]);
      // add trade by input quote amount
      tradeHistoryPage.addTrade(externalTrades[1]);
    });

    it('displays two trades', () => {
      tradeHistoryPage.visibleEntries(2);
      tradeHistoryPage.tradeIsVisible(0, externalTrades[0]);
      tradeHistoryPage.tradeIsVisible(1, externalTrades[1]);
    });

    it('edit external trade', () => {
      tradeHistoryPage.editTrade(0, '123.2');
      tradeHistoryPage.tradeIsVisible(0, {
        ...externalTrades[0],
        amount: '123.2'
      });
    });

    it('delete external trade', () => {
      tradeHistoryPage.deleteTrade(0);
      tradeHistoryPage.confirmDelete();
      tradeHistoryPage.visibleEntries(1);
      tradeHistoryPage.tradeIsVisible(0, externalTrades[1]);
    });
  }
);
