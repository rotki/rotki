import type { FixtureBlockchainAccount } from '../../support/types';
import { BigNumber, Blockchain } from '@rotki/common';
import { waitForAsyncQuery } from '../../support/utils';
import { updateLocationBalance } from '../../utils/amounts';
import { RotkiApp } from '../rotki-app';

export class BlockchainAccountsPage {
  visit(category: string = 'evm') {
    RotkiApp.navigateTo('accounts', `accounts-${category}`);
    cy.assertNoRunningTasks();
  }

  openAddDialog() {
    cy.get('body').then(($body) => {
      if ($body.find('[data-cy=notification]').length > 0) {
        return '[data-cy=notification_dismiss-all]';
      }

      return '';
    }).then((selector) => {
      if (selector) {
        cy.get(selector).click();
      }
    });

    cy.get('[data-cy=notification]').should('not.exist');
    cy.get('[data-cy=add-blockchain-account]').should('be.visible');
    cy.get('[data-cy=add-blockchain-account]').click();
  }

  addAccount(balance: FixtureBlockchainAccount) {
    cy.get('[data-cy=bottom-dialog]').should('be.visible');
    cy.get('[data-cy=blockchain-balance-form]').should('be.visible');
    cy.get('[data-cy=bottom-dialog] [data-cy=account-blockchain-field] input').should('not.be.disabled');
    cy.get('[data-cy=bottom-dialog] [data-cy=account-blockchain-field]').click();
    cy.get('[data-cy=bottom-dialog] [data-cy=account-blockchain-field]').type(balance.chainName);
    cy.get('[role=menu-content] button:first-child').should('contain.text', balance.chainName);
    cy.get('[data-cy=bottom-dialog] [data-cy=account-blockchain-field]').type('{enter}');

    if (balance.blockchain !== Blockchain.ETH)
      cy.get('[data-cy=input-mode-manual]').click();

    cy.get('[data-cy=account-address-field]').should('not.be.disabled');
    cy.get('[data-cy=account-address-field]').type(balance.address);
    cy.get('[data-cy=account-label-field]').type(balance.label);

    for (const tag of balance.tags) {
      cy.get('[data-cy=account-tag-field]').type(`${tag}`);
      cy.get('[data-cy=account-tag-field]').type('{enter}');
    }

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

  editAccount(
    position: number,
    label: string,
  ): void {
    cy.get(`[data-cy=account-table] tbody`)
      .find('tr[class^="_tr_"]:not(tr[class*="_group_"]')
      .eq(position)
      .find('button[data-cy=row-edit]')
      .click();

    cy.get('[data-cy=blockchain-balance-form]').as('edit-form');
    cy.get('@edit-form').find('[data-cy=account-label-field]').as('account-label');
    cy.get('@account-label').click();
    cy.get('@account-label').clear();
    cy.get('@account-label').type(label);
    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').click();
    cy.get('[data-cy=bottom-dialog]', { timeout: 120000 }).should('not.exist');
  }

  confirmDelete() {
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=dialog-title]').should('contain', 'Account delete');
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
  }

  deleteAccount(position: number): void {
    cy.get(`[data-cy=account-table] tbody`)
      .find('tr[class^="_tr_"]:not(tr[class*="_group_"]')
      .eq(position)
      .find('[data-cy=labeled-address-display]')
      .invoke('text')
      .then((label) => {
        cy.get(`[data-cy=account-table] tbody`)
          .find('tr[class^="_tr_"]:not(tr[class*="_group_"]')
          .eq(position)
          .find('button[data-cy=row-delete]')
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
          .find('[data-cy=labeled-address-display]')
          .invoke('text')
          .should('not.contain', label);
      });
  }

  isEntryVisible(position: number, balance: FixtureBlockchainAccount) {
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

    cy.get('@row').find('[data-cy=labeled-address-display]').as('address-label');
    cy.get('@address-label').scrollIntoView();
    cy.get('@address-label').trigger('mouseover');

    cy.get('div[role=tooltip').as('address-tooltip');

    cy.get('@address-tooltip').find('div[role=tooltip-content]').contains(balance.label);
    cy.get('@address-tooltip').find('div[role=tooltip-content]').contains(balance.address);

    for (const tag of balance.tags) cy.get('@row').find('.tag').contains(tag).should('be.visible');

    cy.get('@row').find('[data-cy=labeled-address-display]').as('address-label');
    cy.get('@address-label').scrollIntoView();
    cy.get('@address-label').trigger('mouseleave');
  }

  private getBalances() {
    const balances: Map<string, BigNumber> = new Map();
    const categories = ['evm', 'bitcoin'];

    categories.forEach((category) => {
      this.visit(category);

      cy.get('[data-cy=account-table]')
        .find('tbody')
        .find('tr[class^="_tr_"]:not(tr[class*="_group_"]')
        .each((row) => {
          const value = row.find('[data-cy=usd-value] [data-cy=display-amount]').text();
          const asset = row.find('.account-chain').eq(0).attr('data-chain');

          if (!value || !asset)
            return;

          updateLocationBalance(value, balances, asset.trim().toLowerCase());
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
}
