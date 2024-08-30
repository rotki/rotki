import { BigNumber, Blockchain } from '@rotki/common';
import { setCheckBox, waitForAsyncQuery } from '../../support/utils';
import { RotkiApp } from '../rotki-app';
import { updateLocationBalance } from '../../utils/amounts';

export interface FixtureBlockchainBalance {
  readonly blockchain: Blockchain;
  readonly inputMode: string;
  readonly chainName: string;
  readonly address: string;
  readonly label: string;
  readonly tags: string[];
}

export class BlockchainBalancesPage {
  visit() {
    RotkiApp.navigateTo('accounts-balances', 'accounts-balances-blockchain');
    cy.assertNoRunningTasks();
  }

  openTab(tab: string) {
    cy.get(`[data-cy=${tab}-tab]`).scrollIntoView();
    cy.get(`[data-cy=${tab}-tab]`).click();
    cy.get(`[data-category=${tab}`).should('be.visible');
  }

  addBalance(balance: FixtureBlockchainBalance) {
    cy.get('[data-cy=bottom-dialog]').should('be.visible');
    cy.get('[data-cy="blockchain-balance-form"]').should('be.visible');
    cy.get('[data-cy="account-blockchain-field"] input').should('not.be.disabled');
    cy.get('[data-cy="account-blockchain-field"]').click();
    cy.get('[data-cy="account-blockchain-field"]').type(balance.chainName);
    cy.get('[role=menu-content] button:first-child').should('contain.text', balance.chainName);
    cy.get('[data-cy="account-blockchain-field"]').type('{enter}');

    if (balance.blockchain !== Blockchain.ETH)
      cy.get('[data-cy="input-mode-manual"]').click();

    if (balance.blockchain === Blockchain.ETH)
      setCheckBox('[data-cy="account-all-evm-chains"]', false);

    cy.get('[data-cy="account-address-field"]').should('not.be.disabled');
    cy.get('[data-cy="account-address-field"]').type(balance.address);
    cy.get('[data-cy="account-label-field"]').type(balance.label);

    for (const tag of balance.tags) cy.get('[data-cy="account-tag-field"]').type(`${tag}{enter}`);

    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').click();

    if (balance.blockchain === Blockchain.ETH) {
      waitForAsyncQuery(
        {
          method: 'POST',
          url: '/api/1/assets/prices/latest',
        },
        240000,
      );
    }

    cy.get('[data-cy=bottom-dialog]', { timeout: 120000 }).should('not.exist');
  }

  isEntryVisible(position: number, balance: FixtureBlockchainBalance) {
    // account balances card section for particular blockchain type should be visible
    // sometime the table need long time to be loaded
    cy.get(`[data-cy=account-table]`, {
      timeout: 120000,
    }).as('blockchain-section');

    cy.get('@blockchain-section').should('exist');
    cy.get('@blockchain-section').get('tbody td div[role=progressbar]', { timeout: 300000 }).should('not.exist');

    cy.get('@blockchain-section')
      .find('tbody')
      .find('tr[class^="_tr_"]:not(tr[class*="_group_"]')
      .eq(position)
      .as('row');

    cy.get('@row').find('[data-cy="labeled-address-display"]').as('address-label');
    cy.get('@address-label').scrollIntoView();
    cy.get('@address-label').trigger('mouseover');

    cy.get('div[role=tooltip').as('address-tooltip');

    cy.get('@address-tooltip').find('div[role=tooltip-content]').contains(balance.label);
    cy.get('@address-tooltip').find('div[role=tooltip-content]').contains(balance.address);

    for (const tag of balance.tags) cy.get('@row').find('.tag').contains(tag).should('be.visible');

    cy.get('@row').find('[data-cy="labeled-address-display"]').as('address-label');
    cy.get('@address-label').scrollIntoView();
    cy.get('@address-label').trigger('mouseleave');
  }

  private getBalances() {
    const balances: Map<string, BigNumber> = new Map();
    const categories = ['evm', 'bitcoin'];

    categories.forEach((category) => {
      this.openTab(category);

      cy.get('[data-cy=account-table]')
        .find('tbody')
        .find('tr[class^="_tr_"]:not(tr[class*="_group_"]')
        .each((row) => {
          const usdValue = row.find('td').eq(5).find('[data-cy="display-amount"]').text();
          const asset = row.find('td').eq(2).find('.account-chain').eq(0).attr('data-chain');
          if (!usdValue || !asset)
            return;

          updateLocationBalance(usdValue, balances, asset.trim().toLowerCase());
        });
    });

    return cy.wrap(balances);
  }

  getTotals() {
    return this.getBalances().then(($balances) => {
      let total = new BigNumber(0);
      const balances: { blockchain: string; value: BigNumber }[] = [];

      $balances.forEach((value, blockchain) => {
        total = total.plus(value.toFixed(2, BigNumber.ROUND_DOWN));
        balances.push({ blockchain, value });
      });

      return cy.wrap({
        total,
        balances,
      });
    });
  }

  editBalance(
    position: number,
    label: string,
  ): void {
    cy.get(`[data-cy=account-table] tbody`)
      .find('tr[class^="_tr_"]:not(tr[class*="_group_"]')
      .eq(position)
      .find('button[data-cy="row-edit"]')
      .click();

    cy.get('[data-cy="blockchain-balance-form"]').as('edit-form');
    cy.get('@edit-form').find('[data-cy="account-label-field"]').as('account-label');
    cy.get('@account-label').click();
    cy.get('@account-label').clear();
    cy.get('@account-label').type(label);
    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').click();
    cy.get('[data-cy=bottom-dialog]', { timeout: 120000 }).should('not.exist');
  }

  deleteBalance(position: number): void {
    cy.get(`[data-cy=account-table] tbody`)
      .find('tr[class^="_tr_"]:not(tr[class*="_group_"]')
      .eq(position)
      .find('[data-cy="labeled-address-display"]')
      .invoke('text').then((label) => {
        cy.get(`[data-cy=account-table] tbody`)
          .find('tr[class^="_tr_"]:not(tr[class*="_group_"]')
          .eq(position)
          .find('button[data-cy="row-delete"]')
          .click();

        this.confirmDelete();

        cy.get(`[data-cy=account-table]`, {
          timeout: 120000,
        }).as('blockchain-section');

        cy.get('@blockchain-section').should('exist');
        cy.get('@blockchain-section')
          .get('tbody td div[role=progressbar]', { timeout: 300000 })
          .should('not.exist');

        cy.get(`[data-cy=account-table] tbody`)
          .find('tr[class^="_tr_"]:not(tr[class*="_group_"]')
          .find('[data-cy="labeled-address-display"]')
          .invoke('text')
          .should('not.contain', label);
      });
  }

  confirmDelete() {
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=dialog-title]').should('contain', 'Account delete');
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
  }
}
