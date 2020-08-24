import { Guid } from '../../common/guid';
import { RotkiApp } from '../pages/rotki-app';
import { TradesPage } from '../pages/trades-page';
import { OTCTrade } from '../support/types';

describe('trades', () => {
  let username: string;
  let app: RotkiApp;
  let page: TradesPage;
  let otcData: OTCTrade[];

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new TradesPage();
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
