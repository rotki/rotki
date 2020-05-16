import { default as BigNumber } from 'bignumber.js';
import { ApiManualBalance } from '../../../src/services/types-api';
import { Zero } from '../../../src/utils/bignumbers';
import { Guid } from '../../common/guid';
import { AccountBalancesPage } from '../pages/account-balances-page';
import { DashboardPage } from '../pages/dashboard-page';
import { GeneralSettingsPage } from '../pages/general-settings-page';
import { RotkiApp } from '../pages/rotki-app';
import { TagManager } from '../pages/tag-manager';

describe('Accounts', () => {
  let username: string;
  let app: RotkiApp;
  let page: AccountBalancesPage;
  let dashboardPage: DashboardPage;
  let tagManager: TagManager;
  let settings: GeneralSettingsPage;

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new AccountBalancesPage();
    dashboardPage = new DashboardPage();
    tagManager = new TagManager();
    settings = new GeneralSettingsPage();
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

    it('add second & third entires', () => {
      page.addBalance(manualBalances[1]);
      page.visibleEntries(2);
      page.isVisible(1, manualBalances[1]);
      page.addBalance(manualBalances[2]);
      page.visibleEntries(3);
      page.isVisible(2, manualBalances[2]);
    });

    it('data is reflected in dashboard', () => {
      page.getLocationBalances().then($manualBalances => {
        const total = $manualBalances.reduce((sum: BigNumber, location) => {
          return sum.plus(location.renderedValue.toFixed(2, 1));
        }, Zero);

        dashboardPage.visit();
        dashboardPage.getOverallBalance().then($overallBalance => {
          expect($overallBalance).to.deep.eq(total);
        });
        dashboardPage.getLocationBalances().then($dashboardBalances => {
          expect($dashboardBalances).to.deep.eq($manualBalances);
        });
      });
      page.visit();
    });

    it('test privacy mode is off', () => {
      page.amountDisplayIsNotBlurred();
    });

    it('test privacy mode is on', () => {
      app.togglePrivacyMode();
      page.amountDisplayIsBlurred();
      app.togglePrivacyMode();
    });

    it('test scramble mode', () => {
      page.balanceShouldMatch(manualBalances);

      settings.visit();
      settings.toggleScrambleData();
      page.visit();
      page.balanceShouldNotMatch(manualBalances);

      settings.visit();
      settings.toggleScrambleData();
      page.visit();
    });

    it('edit', () => {
      page.editBalance(1, '200');
      page.visibleEntries(3);
      page.isVisible(1, {
        ...manualBalances[1],
        amount: '200'
      });
    });

    it('delete', () => {
      page.deleteBalance(1);
      page.confirmDelete();
      page.visibleEntries(2);
      page.isVisible(0, manualBalances[0]);
    });
  });
});
