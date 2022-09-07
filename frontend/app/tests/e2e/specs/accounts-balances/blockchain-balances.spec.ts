import { BigNumber } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Zero } from '@/utils/bignumbers';
import { Guid } from '../../../common/guid';
import { AccountBalancesPage } from '../../pages/account-balances-page';
import {
  BlockchainBalancesPage,
  FixtureBlockchainBalance
} from '../../pages/account-balances-page/blockchain-balances-page';
import { DashboardPage } from '../../pages/dashboard-page';
import { RotkiApp } from '../../pages/rotki-app';
import { TagManager } from '../../pages/tag-manager';

describe('blockchain balances', () => {
  let blockchainBalances: FixtureBlockchainBalance[];
  let username: string;
  let app: RotkiApp;
  let page: AccountBalancesPage;
  let blockchainBalancesPage: BlockchainBalancesPage;
  let dashboardPage: DashboardPage;
  let tagManager: TagManager;

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new AccountBalancesPage();
    blockchainBalancesPage = new BlockchainBalancesPage();
    dashboardPage = new DashboardPage();
    tagManager = new TagManager();

    app.fasterLogin(username, '1234', true);

    cy.fixture('account-balances/blockchain-balances').then(balances => {
      blockchainBalances = balances.map((balance: { blockchain: string }) => {
        const address = {
          [Blockchain.ETH]: Cypress.env('ETH_ADDRESS'),
          [Blockchain.BTC]: Cypress.env('BTC_ADDRESS')
        }[balance.blockchain];

        return { ...balance, address };
      });
    });
    page.visit();
    cy.get('.accounts-balances__blockchain-balances').should('be.visible');
    blockchainBalancesPage.visit();
  });

  after(() => {
    app.fasterLogout();
  });

  it('add an ETH account and view the account balance', () => {
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
    blockchainBalancesPage.getBlockchainBalances().then($blockchainBalances => {
      const total = $blockchainBalances.reduce((sum: BigNumber, location) => {
        return sum.plus(
          location.renderedValue.toFixed(2, BigNumber.ROUND_DOWN)
        );
      }, Zero);

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
