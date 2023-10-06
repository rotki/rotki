import { Guid } from '../../common/guid';
import {
  type FixtureManualBalance,
  ManualBalancesPage
} from '../../pages/account-balances-page/manual-balances-page';
import { DashboardPage } from '../../pages/dashboard-page';
import { GeneralSettingsPage } from '../../pages/general-settings-page';
import { RotkiApp } from '../../pages/rotki-app';
import { waitForAsyncQuery } from '../../support/utils';

const PRECISION = 0.1;

describe('balances', () => {
  let username: string;
  let app: RotkiApp;
  let manualBalancesPage: ManualBalancesPage;
  let dashboardPage: DashboardPage;
  let settings: GeneralSettingsPage;
  let manualBalances: FixtureManualBalance[];

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    manualBalancesPage = new ManualBalancesPage();
    dashboardPage = new DashboardPage();
    settings = new GeneralSettingsPage();

    cy.fixture('account-balances/manual-balances').then(balances => {
      manualBalances = balances;
    });
    app.fasterLogin(username);
    manualBalancesPage.visit();
  });

  it('add manual balances', () => {
    cy.get('.manual-balances__add-balance').should('be.visible');

    for (let i = 0; i < 3; i++) {
      cy.get('.manual-balances__add-balance').click();
      const balance = manualBalances[i];
      manualBalancesPage.addBalance(balance);
      manualBalancesPage.visibleEntries(i + 1);
      manualBalancesPage.isVisible(i, balance);
    }

    waitForAsyncQuery({
      method: 'POST',
      url: '/api/1/assets/prices/latest'
    });
  });

  it('change currency', () => {
    app.changeCurrency('EUR');
    manualBalancesPage.showsCurrency('EUR');
  });

  it('data is reflected in dashboard', () => {
    manualBalancesPage.getTotals().then(({ total, balances }) => {
      dashboardPage.visit();
      dashboardPage.getOverallBalance().then($overallBalance => {
        expect($overallBalance.toNumber(), 'total').to.be.within(
          total.minus(PRECISION).toNumber(),
          total.plus(PRECISION).toNumber()
        );
      });
      dashboardPage.getLocationBalances().then($dashboardBalances => {
        expect(
          balances.map(x => x.location),
          'dashboard and manual balances'
        ).to.have.members(Array.from($dashboardBalances.keys()));

        balances.forEach(({ location, value }) => {
          const dashboardBalance = $dashboardBalances.get(location);
          expect(dashboardBalance, `${location} balance`).to.not.be.undefined;
          expect(dashboardBalance?.toNumber(), location).to.be.within(
            value.minus(PRECISION).toNumber(),
            value.plus(PRECISION).toNumber()
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
    manualBalancesPage.visit();
    manualBalancesPage.balanceShouldMatch(manualBalances);

    settings.visit();
    settings.toggleScrambleData();
    manualBalancesPage.visit();
    manualBalancesPage.balanceShouldNotMatch(manualBalances);

    settings.visit();
    settings.toggleScrambleData();
    manualBalancesPage.visit();
  });

  it('test scramble mode from top nav', () => {
    manualBalancesPage.visit();
    app.togglePrivacyMenu(true);
    app.toggleScrambler(false);
    manualBalancesPage.balanceShouldMatch(manualBalances);

    app.toggleScrambler(true);
    manualBalancesPage.balanceShouldNotMatch(manualBalances);

    app.toggleScrambler(false);
    manualBalancesPage.balanceShouldMatch(manualBalances);

    app.changeScrambleValue('0.5');
    manualBalancesPage.balanceShouldNotMatch(manualBalances);

    app.toggleScrambler(false);
    manualBalancesPage.balanceShouldMatch(manualBalances);

    app.changeRandomScrambleValue();
    manualBalancesPage.balanceShouldNotMatch(manualBalances);

    app.toggleScrambler(false);
    manualBalancesPage.balanceShouldMatch(manualBalances);
    app.togglePrivacyMenu();
  });

  it('edit and add', () => {
    const firstNewAmount = '200';
    manualBalancesPage.visit();
    manualBalancesPage.editBalance(1, firstNewAmount);
    manualBalancesPage.visibleEntries(3);
    manualBalancesPage.isVisible(1, {
      ...manualBalances[1],
      amount: firstNewAmount
    });

    const secondNewAmount = '300';
    manualBalancesPage.visit();
    manualBalancesPage.editBalance(1, secondNewAmount);
    manualBalancesPage.visibleEntries(3);
    manualBalancesPage.isVisible(1, {
      ...manualBalances[1],
      amount: secondNewAmount
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
