import { Guid } from '../../common/guid';
import { HistoryPage } from '../pages/history-page';
import { RotkiApp } from '../pages/rotki-app';
import { OTCTrade } from '../support/types';

describe('history', () => {
  let username: string;
  let app: RotkiApp;
  let page: HistoryPage;
  let otcData: OTCTrade[];

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new HistoryPage();
    app.visit();
    app.createAccount(username);
    cy.fixture('otc').then(otc => {
      otcData = otc;
    });
  });

  after(() => {
    app.logout();
  });

  it('add two external trades', () => {
    page.visit();
    page.addTrade(otcData[0]);
    page.addTrade(otcData[1]);
  });

  it('displays two trades', () => {
    page.visibleEntries(2);
    page.tradeIsVisible(0, otcData[0]);
    page.tradeIsVisible(1, otcData[1]);
  });

  it('edit external trade', () => {
    page.editTrade(0, '123.2');
    page.tradeIsVisible(0, {
      ...otcData[0],
      amount: '123.2'
    });
  });

  it('delete external trade', () => {
    page.deleteTrade(0);
    page.confirmDelete();
    page.visibleEntries(1);
    page.tradeIsVisible(0, otcData[1]);
  });
});
