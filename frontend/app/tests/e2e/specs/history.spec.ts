import { Guid } from '../../common/guid';
import { HistoryPage } from '../pages/history-page';
import { RotkiApp } from '../pages/rotki-app';
import { ExternalTrade } from '../support/types';

describe('history', () => {
  let username: string;
  let app: RotkiApp;
  let page: HistoryPage;
  let externalTrades: ExternalTrade[];

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new HistoryPage();
    app.visit();
    app.createAccount(username);
    cy.fixture('trades').then(trade => {
      externalTrades = trade;
    });
  });

  after(() => {
    app.logout();
  });

  it('add two external trades', () => {
    page.visit();
    page.addTrade(externalTrades[0]);
    page.addTrade(externalTrades[1]);
  });

  it('displays two trades', () => {
    page.visibleEntries(2);
    page.tradeIsVisible(0, externalTrades[0]);
    page.tradeIsVisible(1, externalTrades[1]);
  });

  it('edit external trade', () => {
    page.editTrade(0, '123.2');
    page.tradeIsVisible(0, {
      ...externalTrades[0],
      amount: '123.2'
    });
  });

  it('delete external trade', () => {
    page.deleteTrade(0);
    page.confirmDelete();
    page.visibleEntries(1);
    page.tradeIsVisible(0, externalTrades[1]);
  });
});
