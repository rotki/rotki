import { Guid } from '../../common/guid';
import { ApiKeysPage } from '../../pages/api-keys-page';
import { RotkiApp } from '../../pages/rotki-app';

describe('API keys', () => {
  let username: string;
  let app: RotkiApp;
  let page: ApiKeysPage;

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new ApiKeysPage();
    app.fasterLogin(username);
  });

  after(() => {
    app.fasterLogout();
  });

  it('add exchange key', () => {
    const apiKey = Cypress.env('BITTREX_API_KEY');
    const apiSecret = Cypress.env('BITTREX_API_SECRET');
    page.visit();
    page.addExchange(apiKey, apiSecret, 'bittrex', 'BitRex');
    page.exchangeIsAdded('Bittrex', 'BitRex');
  });
});
