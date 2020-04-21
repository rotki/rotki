import { Guid } from '../../common/guid';
import { OtcPage } from '../pages/otc-page';
import { RotkiApp } from '../pages/rotki-app';
import { OTCTrade } from '../support/types';

describe('otc trades', () => {
  let username: string;
  let app: RotkiApp;
  let page: OtcPage;
  let otcData: OTCTrade[];

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new OtcPage();
    app.visit();
    app.createAccount(username);
    app.closePremiumOverlay();
    cy.fixture('otc').then(otc => {
      otcData = otc;
    });
  });

  after(() => {
    app.logout();
  });

  it('add two trades', () => {
    page.visit();
    page.addTrade(otcData[0]);
    page.confirmSuccess();
    page.addTrade(otcData[1]);
    page.confirmSuccess();
  });

  it('displays two trades', () => {
    page.visibleEntries(2);
    page.tradeIsVisible(0, otcData[0]);
    page.tradeIsVisible(1, otcData[1]);
  });

  it('edit trade', () => {
    page.editTrade(0, '123.2');
    page.confirmSuccess();
    page.tradeIsVisible(0, {
      ...otcData[0],
      amount: '123.2'
    });
  });

  it('delete trade', () => {
    page.deleteTrade(0);
    page.confirmDelete();
    page.visibleEntries(1);
    page.tradeIsVisible(0, otcData[1]);
  });
});
