import { BigNumber } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Zero } from '@/utils/bignumbers';
import { Guid } from '../../common/guid';
import {
  BlockchainBalancesPage,
  type FixtureBlockchainBalance
} from '../../pages/account-balances-page/blockchain-balances-page';
import { DashboardPage } from '../../pages/dashboard-page';
import { RotkiApp } from '../../pages/rotki-app';
import { TagManager } from '../../pages/tag-manager';

describe('blockchain balances', () => {
  let blockchainBalances: FixtureBlockchainBalance[];
  let username: string;
  let app: RotkiApp;
  let blockchainBalancesPage: BlockchainBalancesPage;
  let dashboardPage: DashboardPage;
  let tagManager: TagManager;

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
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
    blockchainBalancesPage.visit();
  });

  it('add an ETH account and view the account balance', () => {
    cy.get('[data-cy="add-blockchain-balance"]').should('be.visible');
    cy.get('[data-cy="add-blockchain-balance"]').click();
    tagManager.addTag(
      '[data-cy="account-tag-field"]',
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
      const total = $blockchainBalances.reduce(
        (sum: BigNumber, location) =>
          sum.plus(location.value.toFixed(2, BigNumber.ROUND_DOWN)),
        Zero
      );

      dashboardPage.visit();
      dashboardPage.getOverallBalance().then($overallBalance => {
        dashboardPage.getNonFungibleBalances().then($nonFungibleBalance => {
          // compare overall balance with blockchain balance + non-fungible balance,
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
        $dashboardBalances.forEach((dashboardBalances, index) => {
          const { blockchain, value } = $blockchainBalances[index];
          const dashboardValue = dashboardBalances.value;
          expect(dashboardValue.toNumber(), blockchain).within(
            value.minus(0.01).toNumber(),
            value.plus(0.01).toNumber()
          );
        });
      });
    });
  });

  it('edit', () => {
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
