import { ApiManualBalance } from '../../../src/services/types-api';
import { Guid } from '../../common/guid';
import { AccountBalancesPage } from '../pages/account-balances-page';
import { RotkiApp } from '../pages/rotki-app';
import { TagManager } from '../pages/tag-manager';

describe('Accounts', () => {
  let username: string;
  let app: RotkiApp;
  let page: AccountBalancesPage;
  let tagManager: TagManager;

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new AccountBalancesPage();
    tagManager = new TagManager();
    app.visit();
    app.createAccount(username);
    app.closePremiumOverlay();
    page.visit();
  });

  after(() => {
    app.logout();
  });

  describe('manual balances', () => {
    let manualBalances: ApiManualBalance[];
    before(() => {
      cy.fixture('manual-balances').then(balances => {
        manualBalances = balances;
      });
    });

    it('add first entry', () => {
      tagManager.addTag(
        '.manual-balances-form',
        'public',
        'Public Accounts',
        '#EF703C',
        '#FFFFF8'
      );
      page.addBalance(manualBalances[0]);
      page.visibleEntries(1);
      page.isVisible(0, manualBalances[0]);
    });

    it('change currency', () => {
      app.changeCurrency('EUR');
      page.showsCurrency('EUR');
    });

    it('add second entry', () => {
      page.addBalance(manualBalances[1]);
      page.visibleEntries(2);
      page.isVisible(1, manualBalances[1]);
    });

    it('edit', () => {
      page.editBalance(1, '200');
      page.visibleEntries(2);
      page.isVisible(1, {
        ...manualBalances[1],
        amount: '200'
      });
    });

    it('delete', () => {
      page.deleteBalance(1);
      page.confirmDelete();
      page.visibleEntries(1);
      page.isVisible(0, manualBalances[0]);
    });
  });
});
