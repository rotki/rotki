import type { FixtureBlockchainAccount } from '../../support/types';
import { Blockchain } from '@rotki/common';
import { BlockchainAccountsPage } from '../../pages/accounts-page/blockchain-accounts-page';
import {
  BlockchainBalancesPage,
} from '../../pages/balances-page/blockchain-balances-page';
import { DashboardPage } from '../../pages/dashboard-page';
import { RotkiApp } from '../../pages/rotki-app';
import { TagManager } from '../../pages/tag-manager';
import { createUser } from '../../utils/user';

const PRECISION = 0.1;

describe('blockchain balances', () => {
  let blockchainAccounts: FixtureBlockchainAccount[];
  let username: string;
  let app: RotkiApp;
  let blockchainAccountsPage: BlockchainAccountsPage;
  let blockchainBalancesPage: BlockchainBalancesPage;
  let dashboardPage: DashboardPage;
  let tagManager: TagManager;

  before(() => {
    username = createUser();
    app = new RotkiApp();
    blockchainAccountsPage = new BlockchainAccountsPage();
    blockchainBalancesPage = new BlockchainBalancesPage();
    dashboardPage = new DashboardPage();
    tagManager = new TagManager();

    app.fasterLogin(username, '1234', true);

    cy.fixture('account-balances/blockchain-accounts').then((accounts) => {
      blockchainAccounts = accounts.map((account: { blockchain: string }) => {
        const address = {
          [Blockchain.ETH]: Cypress.env('ETH_ADDRESS'),
          [Blockchain.BTC]: Cypress.env('BTC_ADDRESS'),
        }[account.blockchain];

        return { ...account, address };
      });
    });
  });

  it('add an ETH account and view the account balance', () => {
    blockchainAccountsPage.visit();
    blockchainAccountsPage.openAddDialog();
    tagManager.addTag('[data-cy=account-tag-field]', 'public', 'Public Accounts', 'EF703C', 'FFFFF8');
    blockchainAccountsPage.addAccount(blockchainAccounts[0]);
    blockchainAccountsPage.isEntryVisible(0, blockchainAccounts[0]);
    cy.get('[data-cy=blockchain-account-refresh]').should('not.be.disabled');
    cy.assertNoRunningTasks();
  });

  it('add a BTC account and view the account balance', () => {
    blockchainAccountsPage.visit('bitcoin');
    blockchainAccountsPage.openAddDialog();
    blockchainAccountsPage.addAccount(blockchainAccounts[1]);
    blockchainAccountsPage.isEntryVisible(0, blockchainAccounts[1]);
    cy.get('[data-cy=blockchain-account-refresh]').should('not.be.disabled');
    cy.assertNoRunningTasks();
  });

  it('data is reflected in dashboard', () => {
    blockchainAccountsPage.getTotals().then(({ total, balances }) => {
      dashboardPage.visit();
      dashboardPage.getOverallBalance().then(($overallBalance) => {
        dashboardPage.getNonFungibleBalances().then(($nonFungibleBalance) => {
          const totalPlusNft = total.plus($nonFungibleBalance);
          expect($overallBalance.toNumber(), 'overall balance').to.be.within(
            totalPlusNft.minus(PRECISION).toNumber(),
            totalPlusNft.plus(PRECISION).toNumber(),
          );
        });
      });

      dashboardPage.getBlockchainBalances().then(($dashboardBalances) => {
        expect(
          balances.filter(x => x.value.gt(0)).map(x => x.blockchain),
          'dashboard and blockchain balances',
        ).to.have.members(Array.from($dashboardBalances.keys()));

        balances.forEach(({ blockchain, value }) => {
          const dashboardBalance = $dashboardBalances.get(blockchain);
          const label = `${blockchain} balance`;
          if (value.gt(0)) {
            // eslint-disable-next-line @typescript-eslint/no-unused-expressions
            expect(dashboardBalance, label).to.not.be.undefined;
            expect(dashboardBalance?.toNumber(), blockchain).to.be.within(
              value.minus(PRECISION).toNumber(),
              value.plus(PRECISION).toNumber(),
            );
          }
          else {
            // eslint-disable-next-line @typescript-eslint/no-unused-expressions
            expect(dashboardBalance, label).to.be.undefined;
          }
        });

        blockchainBalancesPage.getTotals().then(($blockchainBalancesTotal) => {
          expect($blockchainBalancesTotal.toNumber(), 'overall balance').to.be.within(
            total.minus(PRECISION).toNumber(),
            total.plus(PRECISION).toNumber(),
          );
        });
      });
    });
  });

  it('edit', () => {
    const newLabel = 'New ETH label';
    blockchainAccountsPage.visit();
    blockchainAccountsPage.editAccount(0, newLabel);

    blockchainAccountsPage.isEntryVisible(0, {
      ...blockchainAccounts[0],
      label: newLabel,
    });
  });

  it('delete', () => {
    blockchainAccountsPage.visit();

    // Delete ETH entry
    blockchainAccountsPage.deleteAccount(0);

    // Delete BTC entry
    blockchainAccountsPage.visit('bitcoin');
    blockchainAccountsPage.deleteAccount(0);
  });
});
