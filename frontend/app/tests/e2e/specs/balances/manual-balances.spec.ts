import { BigNumber } from '@rotki/common';
import { Guid } from '../../common/guid';
import { AccountBalancesPage } from '../../pages/account-balances-page';
import {
  type FixtureManualBalance,
  ManualBalancesPage
} from '../../pages/account-balances-page/manual-balances-page';
import { DashboardPage } from '../../pages/dashboard-page';
import { GeneralSettingsPage } from '../../pages/general-settings-page';
import { RotkiApp } from '../../pages/rotki-app';
import { waitForAsyncQuery } from '../../support/utils';

describe('balances', () => {
  let username: string;
  let app: RotkiApp;
  let page: AccountBalancesPage;
  let manualBalancesPage: ManualBalancesPage;
  let dashboardPage: DashboardPage;
  let settings: GeneralSettingsPage;
  let manualBalances: FixtureManualBalance[];

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new AccountBalancesPage();
    manualBalancesPage = new ManualBalancesPage();
    dashboardPage = new DashboardPage();
    settings = new GeneralSettingsPage();
    app.fasterLogin(username);
    page.visit();
    cy.fixture('account-balances/manual-balances').then(balances => {
      manualBalances = balances;
    });
    manualBalancesPage.visit();
  });

  after(() => {
    app.fasterLogout();
  });

  it('add first entry', () => {
    cy.get('.manual-balances__add-balance').should('be.visible');
    cy.get('.manual-balances__add-balance').click();
    manualBalancesPage.addBalance(manualBalances[0]);
    manualBalancesPage.visibleEntries(1);
    manualBalancesPage.isVisible(0, manualBalances[0]);
  });

  it('change currency', () => {
    app.changeCurrency('EUR');
    manualBalancesPage.showsCurrency('EUR');
  });

  it('add second & third entires', () => {
    cy.get('.manual-balances__add-balance').click();
    manualBalancesPage.addBalance(manualBalances[1]);
    manualBalancesPage.visibleEntries(2);
    manualBalancesPage.isVisible(1, manualBalances[1]);

    cy.get('.manual-balances__add-balance').click();
    manualBalancesPage.addBalance(manualBalances[2]);
    manualBalancesPage.visibleEntries(3);
    manualBalancesPage.isVisible(2, manualBalances[2]);

    waitForAsyncQuery({
      method: 'POST',
      url: '/api/1/assets/prices/latest'
    });
  });

  it('data is reflected in dashboard', () => {
    manualBalancesPage.getLocationBalances().then($manualBalances => {
      const total = $manualBalances.reduce(
        (sum: BigNumber, location) =>
          sum.plus(location.value.toFixed(2, BigNumber.ROUND_DOWN)),
        Zero
      );
      dashboardPage.visit();
      dashboardPage.getOverallBalance().then($overallBalance => {
        // compare overall balance with blockchain balance
        // with tolerance 0.01 (precision = 2)
        expect($overallBalance.minus(total).abs().isLessThan(0.01));
      });
      dashboardPage.getLocationBalances().then($dashboardBalances => {
        $dashboardBalances.forEach((dashboardBalances, index) => {
          const { location, value } = $manualBalances[index];
          const dashboardBalance = dashboardBalances.value;
          expect(dashboardBalance.toNumber(), location).within(
            value.minus(0.01).toNumber(),
            value.plus(0.01).toNumber()
          );
        });
      });
    });
  });

  it('test privacy mode is off', () => {
    dashboardPage.amountDisplayIsNotBlurred();
    dashboardPage.percentageDisplayIsNotBlurred();
  });

  it('test privacy mode is semi private', () => {
    app.changePrivacyMode(1);
    dashboardPage.amountDisplayIsBlurred();
    dashboardPage.percentageDisplayIsNotBlurred();
    app.changePrivacyMode(0);
  });

  it('test privacy mode is private', () => {
    app.changePrivacyMode(2);
    dashboardPage.amountDisplayIsBlurred();
    dashboardPage.percentageDisplayIsBlurred();
    app.changePrivacyMode(0);
  });

  it('test scramble mode', () => {
    page.visit();
    manualBalancesPage.visit();
    manualBalancesPage.balanceShouldMatch(manualBalances);

    settings.visit();
    settings.toggleScrambleData();
    page.visit();
    manualBalancesPage.visit();
    manualBalancesPage.balanceShouldNotMatch(manualBalances);

    settings.visit();
    settings.toggleScrambleData();
    page.visit();
    manualBalancesPage.visit();
  });

  it('edit', () => {
    const newAmount = '200';
    manualBalancesPage.visit();
    manualBalancesPage.editBalance(1, newAmount);
    manualBalancesPage.visibleEntries(3);
    manualBalancesPage.isVisible(1, {
      ...manualBalances[1],
      amount: newAmount
    });
  });

  it('edit and add new', () => {
    const newAmount = '300';
    manualBalancesPage.visit();
    manualBalancesPage.editBalance(1, newAmount);
    manualBalancesPage.visibleEntries(3);
    manualBalancesPage.isVisible(1, {
      ...manualBalances[1],
      amount: newAmount
    });

    cy.get('.manual-balances__add-balance').click();

    const apiManualBalance = { ...manualBalances[1], label: 'extra' };
    manualBalancesPage.addBalance(apiManualBalance);
    manualBalancesPage.visibleEntries(4);
    manualBalancesPage.isVisible(2, apiManualBalance);
  });

  it('delete', () => {
    manualBalancesPage.visit();
    manualBalancesPage.deleteBalance(1);
    manualBalancesPage.visibleEntries(3);
    manualBalancesPage.isVisible(0, manualBalances[0]);
  });
});
