import { BigNumber } from '@rotki/common/';
import { Zero } from '@/utils/bignumbers';
import { Guid } from '../../common/guid';
import {
  AccountBalancesPage,
  FixtureManualBalance
} from '../pages/account-balances-page';
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
    page.visit();
  });

  after(() => {
    app.logout();
  });

  function goToManualBalances() {
    cy.get('.accounts-balances__manual-balances').click({
      force: true
    });
  }

  describe('manual balances', () => {
    let manualBalances: FixtureManualBalance[];
    before(() => {
      cy.fixture('manual-balances').then(balances => {
        manualBalances = balances;
      });
      cy.get('.accounts-balances__manual-balances').should('be.visible');
      goToManualBalances();
    });

    it('add first entry', () => {
      cy.get('.manual-balances__add-balance').should('be.visible');
      cy.get('.manual-balances__add-balance').click();
      tagManager.addTag(
        '[data-cy="manual-balance-form"]',
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
      cy.get('.manual-balances__add-balance').click();
      page.addBalance(manualBalances[1]);
      page.visibleEntries(2);
      page.isVisible(1, manualBalances[1]);

      cy.get('.manual-balances__add-balance').click();
      page.addBalance(manualBalances[2]);
      page.visibleEntries(3);
      page.isVisible(2, manualBalances[2]);
    });

    it('data is reflected in dashboard', () => {
      page.getLocationBalances().then($manualBalances => {
        const total = $manualBalances.reduce((sum: BigNumber, location) => {
          return sum.plus(
            location.renderedValue.toFixed(2, BigNumber.ROUND_DOWN)
          );
        }, Zero);

        dashboardPage.visit();
        dashboardPage.getOverallBalance().then($overallBalance => {
          expect($overallBalance.toString()).to.eq(total.toString());
        });
        dashboardPage.getLocationBalances().then($dashboardBalances => {
          expect($dashboardBalances.toString()).to.eq(
            $manualBalances.toString()
          );
        });
      });
      page.visit();
    });

    it('test privacy mode is off', () => {
      goToManualBalances();
      page.amountDisplayIsNotBlurred();
    });

    it('test privacy mode is on', () => {
      goToManualBalances();
      app.togglePrivacyMode();
      page.amountDisplayIsBlurred();
      app.togglePrivacyMode();
    });

    it('test scramble mode', () => {
      goToManualBalances();
      page.balanceShouldMatch(manualBalances);

      settings.visit();
      settings.toggleScrambleData();
      page.visit();
      goToManualBalances();
      page.balanceShouldNotMatch(manualBalances);

      settings.visit();
      settings.toggleScrambleData();
      page.visit();
      goToManualBalances();
    });

    it('edit', () => {
      goToManualBalances();
      page.editBalance(1, '200');
      page.visibleEntries(3);
      page.isVisible(1, {
        ...manualBalances[1],
        amount: '200'
      });
    });

    it('edit and add new', function () {
      goToManualBalances();
      page.editBalance(1, '300');
      page.visibleEntries(3);
      page.isVisible(1, {
        ...manualBalances[1],
        amount: '300'
      });

      cy.get('.manual-balances__add-balance').click();

      const apiManualBalance = { ...manualBalances[1], label: 'extra' };
      page.addBalance(apiManualBalance);
      page.visibleEntries(4);
      page.isVisible(2, apiManualBalance);
    });

    it('delete', () => {
      goToManualBalances();
      page.deleteBalance(1);
      page.confirmDelete();
      page.visibleEntries(3);
      page.isVisible(0, manualBalances[0]);
    });
  });
});
