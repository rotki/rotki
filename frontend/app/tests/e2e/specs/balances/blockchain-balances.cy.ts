import { Blockchain } from '@rotki/common';
import {
  BlockchainBalancesPage,
  type FixtureBlockchainBalance,
} from '../../pages/account-balances-page/blockchain-balances-page';
import { DashboardPage } from '../../pages/dashboard-page';
import { RotkiApp } from '../../pages/rotki-app';
import { TagManager } from '../../pages/tag-manager';
import { createUser } from '../../utils/user';

const PRECISION = 0.1;

describe('blockchain balances', () => {
  let blockchainBalances: FixtureBlockchainBalance[];
  let username: string;
  let app: RotkiApp;
  let blockchainBalancesPage: BlockchainBalancesPage;
  let dashboardPage: DashboardPage;
  let tagManager: TagManager;

  before(() => {
    username = createUser();
    app = new RotkiApp();
    blockchainBalancesPage = new BlockchainBalancesPage();
    dashboardPage = new DashboardPage();
    tagManager = new TagManager();

    app.fasterLogin(username, '1234', true);

    cy.fixture('account-balances/blockchain-balances').then((balances) => {
      blockchainBalances = balances.map((balance: { blockchain: string }) => {
        const address = {
          [Blockchain.ETH]: Cypress.env('ETH_ADDRESS'),
          [Blockchain.BTC]: Cypress.env('BTC_ADDRESS'),
        }[balance.blockchain];

        return { ...balance, address };
      });
    });
    blockchainBalancesPage.visit();
  });

  it('add an ETH account and view the account balance', () => {
    blockchainBalancesPage.openAddDialog();
    tagManager.addTag('[data-cy=account-tag-field]', 'public', 'Public Accounts', 'EF703C', 'FFFFF8');
    blockchainBalancesPage.addBalance(blockchainBalances[0]);
    blockchainBalancesPage.isEntryVisible(0, blockchainBalances[0]);
    cy.get('[data-cy=price-refresh]', { timeout: 120000 }).should('not.be.disabled');
    cy.assertNoRunningTasks();
  });

  it('add a BTC account and view the account balance', () => {
    blockchainBalancesPage.openAddDialog();
    blockchainBalancesPage.addBalance(blockchainBalances[1]);
    blockchainBalancesPage.openTab('bitcoin');
    blockchainBalancesPage.isEntryVisible(0, blockchainBalances[1]);
    cy.get('[data-cy=price-refresh]', { timeout: 120000 }).should('not.be.disabled');
    cy.assertNoRunningTasks();
  });

  it('data is reflected in dashboard', () => {
    blockchainBalancesPage.getTotals().then(({ total, balances }) => {
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
      });
    });
  });

  it('edit', () => {
    const newLabel = 'New ETH label';
    blockchainBalancesPage.visit();
    blockchainBalancesPage.editBalance(0, newLabel);

    blockchainBalancesPage.isEntryVisible(0, {
      ...blockchainBalances[0],
      label: newLabel,
    });
  });

  it('delete', () => {
    blockchainBalancesPage.visit();

    // Delete ETH entry
    blockchainBalancesPage.openTab('evm');
    blockchainBalancesPage.deleteBalance(0);

    // Delete BTC entry
    blockchainBalancesPage.openTab('bitcoin');
    blockchainBalancesPage.deleteBalance(0);
  });
});
