import { BigNumber } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Zero } from '@/utils/bignumbers';
import { Guid } from '../../common/guid';
import { AccountBalancesPage } from '../pages/account-balances-page';
import {
  BlockchainBalancesPage,
  FixtureBlockchainBalance
} from '../pages/account-balances-page/blockchain-balances-page';
import {
  FixtureManualBalance,
  ManualBalancesPage
} from '../pages/account-balances-page/manual-balances-page';
import { DashboardPage } from '../pages/dashboard-page';
import { GeneralSettingsPage } from '../pages/general-settings-page';
import { RotkiApp } from '../pages/rotki-app';
import { TagManager } from '../pages/tag-manager';

describe('balances', () => {
  let username: string;
  let app: RotkiApp;
  let page: AccountBalancesPage;
  let manualBalancesPage: ManualBalancesPage;
  let blockchainBalancesPage: BlockchainBalancesPage;
  let dashboardPage: DashboardPage;
  let tagManager: TagManager;
  let settings: GeneralSettingsPage;

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new AccountBalancesPage();
    manualBalancesPage = new ManualBalancesPage();
    blockchainBalancesPage = new BlockchainBalancesPage();
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

  describe('blockchain balances', () => {
    let blockchainBalances: FixtureBlockchainBalance[];
    before(() => {
      cy.fixture('account-balances/blockchain-balances').then(balances => {
        blockchainBalances = balances.map((balance: { blockchain: string }) => {
          const address = {
            [Blockchain.ETH]: Cypress.env('ETH_ADDRESS'),
            [Blockchain.BTC]: Cypress.env('BTC_ADDRESS')
          }[balance.blockchain];

          return { ...balance, address };
        });
      });
      cy.get('.accounts-balances__blockchain-balances').should('be.visible');
      blockchainBalancesPage.visit();
    });

    it('add an ETH account and view the account balance', () => {
      cy.disableModules();
      cy.get('[data-cy="add-blockchain-balance"]').should('be.visible');
      cy.get('[data-cy="add-blockchain-balance"]').click();
      tagManager.addTag(
        '[data-cy="blockchain-balance-form"]',
        'public',
        'Public Accounts',
        '#EF703C',
        '#FFFFF8'
      );
      blockchainBalancesPage.addBalance(blockchainBalances[0]);
      blockchainBalancesPage.isEntryVisible(0, blockchainBalances[0]);
    });

    it('add a BTC account and view the account balance', () => {
      cy.get('[data-cy="add-blockchain-balance"]').should('be.visible');
      cy.get('[data-cy="add-blockchain-balance"]').click();
      blockchainBalancesPage.addBalance(blockchainBalances[1]);
      blockchainBalancesPage.isEntryVisible(0, blockchainBalances[1]);
    });

    it('data is reflected in dashboard', () => {
      blockchainBalancesPage
        .getBlockchainBalances()
        .then($blockchainBalances => {
          const total = $blockchainBalances.reduce(
            (sum: BigNumber, location) => {
              return sum.plus(
                location.renderedValue.toFixed(2, BigNumber.ROUND_DOWN)
              );
            },
            Zero
          );

          dashboardPage.visit();
          dashboardPage.getOverallBalance().then($overallBalance => {
            dashboardPage.getNonFungibleBalances().then($nonFungibleBalance => {
              // compare overall balance with blockchain balance + non fungible balance,
              // with tolerance 0.01 (precision = 2)
              expect(
                $overallBalance
                  .minus(total.plus($nonFungibleBalance))
                  .abs()
                  .isLessThan(0.01)
              );
            });
          });
          dashboardPage.getBlockchainBalances().then($dashboardBalances => {
            expect($dashboardBalances).to.deep.eq($blockchainBalances);
          });
        });
    });

    it('edit', () => {
      page.visit();
      const newLabel = 'New ETH label';
      blockchainBalancesPage.visit();
      blockchainBalancesPage.editBalance(blockchainBalances[0], 0, newLabel);

      blockchainBalancesPage.isEntryVisible(0, {
        ...blockchainBalances[0],
        label: newLabel
      });
    });

    it('delete', () => {
      blockchainBalancesPage.visit();

      // Delete ETH entry
      blockchainBalancesPage.deleteBalance(blockchainBalances[0], 0);

      // Delete BTC entry
      blockchainBalancesPage.deleteBalance(blockchainBalances[1], 0);
    });
  });

  describe('manual balances', () => {
    let manualBalances: FixtureManualBalance[];
    before(() => {
      cy.fixture('account-balances/manual-balances').then(balances => {
        manualBalances = balances;
      });
      manualBalancesPage.visit();
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
    });

    it('data is reflected in dashboard', () => {
      manualBalancesPage.getLocationBalances().then($manualBalances => {
        const total = $manualBalances.reduce((sum: BigNumber, location) => {
          return sum.plus(
            location.renderedValue.toFixed(2, BigNumber.ROUND_DOWN)
          );
        }, Zero);
        dashboardPage.visit();
        dashboardPage.getOverallBalance().then($overallBalance => {
          // compare overall balance with blockchain balance
          // with tolerance 0.01 (precision = 2)
          expect($overallBalance.minus(total).abs().isLessThan(0.01));
        });
        dashboardPage.getLocationBalances().then($dashboardBalances => {
          expect($dashboardBalances).to.deep.eq($manualBalances);
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

    it('edit and add new', function () {
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
});
