import { Guid } from '../../common/guid';
import { HistoryPage } from '../pages/history-page';
import { LedgerActionPage } from '../pages/history-page/ledger-action-page';
import { TradeHistoryPage } from '../pages/history-page/trade-history-page';
import { RotkiApp } from '../pages/rotki-app';
import { ExternalLedgerAction, ExternalTrade } from '../support/types';

describe('history', () => {
  let username: string;
  let app: RotkiApp;
  let page: HistoryPage;
  let tradeHistoryPage: TradeHistoryPage;
  let ledgerActionPage: LedgerActionPage;

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new HistoryPage();
    tradeHistoryPage = new TradeHistoryPage();
    ledgerActionPage = new LedgerActionPage();
    app.visit();
    app.createAccount(username);
    page.visit();
  });

  after(() => {
    app.logout();
  });

  describe('trades history', () => {
    let externalTrades: ExternalTrade[];
    before(() => {
      cy.fixture('history/trades').then(trade => {
        externalTrades = trade;
      });
      tradeHistoryPage.visit();
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
  });

  describe('ledger actions history', () => {
    let externalLedgerActions: ExternalLedgerAction[];
    before(() => {
      cy.fixture('history/ledger-actions').then(ledgerAction => {
        externalLedgerActions = ledgerAction;
      });
      ledgerActionPage.visit();
    });

    it('add two ledger actions', () => {
      ledgerActionPage.addLedgerAction(externalLedgerActions[0]);
      ledgerActionPage.addLedgerAction(externalLedgerActions[1]);
    });

    it('displays two ledger actions', () => {
      ledgerActionPage.visibleEntries(2);
      ledgerActionPage.ledgerActionIsVisible(0, externalLedgerActions[0]);
      ledgerActionPage.ledgerActionIsVisible(1, externalLedgerActions[1]);
    });

    it('edit ledger action', () => {
      ledgerActionPage.editTrade(0, '123.2');
      ledgerActionPage.ledgerActionIsVisible(0, {
        ...externalLedgerActions[0],
        amount: '123.2'
      });
    });

    it('delete ledger action', () => {
      ledgerActionPage.deleteLedgerAction(0);
      ledgerActionPage.confirmDelete();
      ledgerActionPage.visibleEntries(1);
      ledgerActionPage.ledgerActionIsVisible(0, externalLedgerActions[1]);
    });
  });
});
