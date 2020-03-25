import { Guid } from '../../common/guid';
import { RotkiApp } from '../pages/rotki-app';
import { ApiKeysPage } from '../pages/api-keys-page';

describe('API keys', () => {
  let username: string;
  let app: RotkiApp;
  let page: ApiKeysPage;

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new ApiKeysPage();
    app.visit();
    app.createAccount(username);
    app.closePremiumOverlay();
  });

  after(() => {
    app.logout();
  });

  it('add exchange key', () => {
    const apiKey = Cypress.env('BITTREX_API_KEY');
    const apiSecret = Cypress.env('BITTREX_API_SECRET');
    page.visit();
    page.addExchange(apiKey, apiSecret, 'bittrex');
    page.exchangeIsAdded('bittrex');
  });
});
