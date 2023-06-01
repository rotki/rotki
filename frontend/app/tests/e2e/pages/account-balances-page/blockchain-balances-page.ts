import { Blockchain } from '@rotki/common/lib/blockchain';
import { Zero, bigNumberify } from '@/utils/bignumbers';
import { setCheckBox, waitForAsyncQuery } from '../../support/utils';
import { AccountBalancesPage } from './index';

export interface FixtureBlockchainBalance {
  readonly blockchain: Blockchain;
  readonly inputMode: string;
  readonly chainName: string;
  readonly address: string;
  readonly label: string;
  readonly tags: string[];
}

export class BlockchainBalancesPage extends AccountBalancesPage {
  visit() {
    cy.get('.accounts-balances__blockchain-balances').scrollIntoView();
    cy.get('.accounts-balances__blockchain-balances').should('be.visible');
    cy.get('.accounts-balances__blockchain-balances').click();
  }

  isGroupped(balance: FixtureBlockchainBalance) {
    return balance.blockchain === Blockchain.ETH;
  }

  addBalance(balance: FixtureBlockchainBalance) {
    cy.get('.big-dialog').should('be.visible');
    cy.get('[data-cy="blockchain-balance-form"]').should('be.visible');
    cy.get('[data-cy="account-blockchain-field"]').parent().click();
    cy.get('.v-menu__content').contains(balance.chainName).click();
    cy.get('[data-cy="input-mode-manual"]').click();

    if (balance.blockchain === Blockchain.ETH) {
      setCheckBox('[data-cy="account-all-evm-chains"]', false);
    }

    cy.get('[data-cy="account-address-field"]').type(balance.address);
    cy.get('[data-cy="account-label-field"]').type(balance.label);

    for (const tag of balance.tags) {
      cy.get('[data-cy="account-tag-field"]').type(tag);
      cy.get('[data-cy="account-tag-field"]').type('{enter}');
    }

    cy.get('.big-dialog__buttons__confirm').click();

    if (balance.blockchain === Blockchain.ETH) {
      waitForAsyncQuery(
        {
          method: 'POST',
          url: '/api/1/assets/prices/latest'
        },
        240000
      );
    }

    cy.get('.big-dialog', { timeout: 120000 }).should('not.be.visible');
  }

  isEntryVisible(position: number, balance: FixtureBlockchainBalance) {
    // account balances card section for particular blockchain type should be visible
    // sometime the table need long time to be loaded
    cy.get(`[data-cy="blockchain-balances-${balance.blockchain}"]`, {
      timeout: 120000
    }).as('blockchain-section');

    cy.get('@blockchain-section').should('exist');
    cy.get('@blockchain-section')
      .get('.v-data-table__progress', { timeout: 300000 })
      .should('not.exist');

    cy.get('@blockchain-section')
      .find('[data-cy="blockchain-balances"] tbody')
      .find('tr')
      .eq(position + (this.isGroupped(balance) ? 0 : 1))
      .as('row');

    cy.get('@row')
      .find('[data-cy="labeled-address-display"]')
      .as('address-label');
    cy.get('@address-label').scrollIntoView();
    cy.get('@address-label').trigger('mouseenter');

    cy.get('.v-tooltip__content.menuable__content__active').as(
      'address-tooltip'
    );

    cy.get('@address-tooltip')
      .find('div:nth-child(1)')
      .find('span')
      .contains(balance.label);
    cy.get('@address-tooltip')
      .find('div:nth-child(2)')
      .contains(balance.address);

    for (const tag of balance.tags) {
      cy.get('@row').find('.tag').contains(tag).should('be.visible');
    }

    cy.get('@row')
      .find('[data-cy="labeled-address-display"]')
      .as('address-label');
    cy.get('@address-label').scrollIntoView();
    cy.get('@address-label').trigger('mouseleave');
  }

  getBlockchainBalances() {
    const blockchainBalances = [
      { blockchain: 'Ethereum', symbol: Blockchain.ETH, value: Zero },
      { blockchain: 'Bitcoin', symbol: Blockchain.BTC, value: Zero }
    ];

    cy.get('[data-cy=blockchain-asset-balances] .v-data-table__empty-wrapper', {
      timeout: 300000
    }).should('not.exist');

    blockchainBalances.forEach(blockchainBalance => {
      const tableClass = `[data-cy="blockchain-balances-${blockchainBalance.symbol}"]`;
      cy.get(tableClass).scrollIntoView();
      cy.get('body').then($body => {
        if ($body.find(tableClass).length > 0) {
          cy.get(`${tableClass} .v-data-table__progress`, {
            timeout: 240000
          }).should('not.be.exist');

          cy.get(
            `${tableClass} tr:contains(${blockchainBalance.symbol.toUpperCase()}) td:nth-child(4) [data-cy="display-amount"]`,
            {
              timeout: 120000
            }
          ).each($amount => {
            blockchainBalance.value = blockchainBalance.value.plus(
              bigNumberify(this.getSanitizedAmountString($amount.text()))
            );
          });
        }
      });
    });

    return cy.wrap(blockchainBalances);
  }

  editBalance(
    balance: FixtureBlockchainBalance,
    position: number,
    label: string
  ) {
    cy.get(`[data-cy="blockchain-balances-${balance.blockchain}"] tbody`)
      .find('tr')
      .eq(position + (this.isGroupped(balance) ? 0 : 1))
      .find('button.actions__edit')
      .click();

    cy.get('[data-cy="blockchain-balance-form"]').as('edit-form');
    cy.get('@edit-form')
      .find('[data-cy="account-label-field"]')
      .as('account-label');
    cy.get('@account-label').click();
    cy.get('@account-label').clear();
    cy.get('@account-label').type(label);
    cy.get('.big-dialog__buttons__confirm').click();
    cy.get('[data-cy=bottom-dialog]', { timeout: 120000 }).should(
      'not.be.visible'
    );
  }

  deleteBalance(balance: FixtureBlockchainBalance, position: number) {
    cy.get(`[data-cy="blockchain-balances-${balance.blockchain}"] tbody`)
      .find('tr')
      .eq(position + (this.isGroupped(balance) ? 0 : 1))
      .find('[data-cy="account-balances-item-checkbox"]')
      .click();

    cy.get(`[data-cy="blockchain-balances-${balance.blockchain}"]`)
      .find('[data-cy="account-balances__delete-button"]')
      .click();

    this.confirmDelete();

    cy.get(`[data-cy="blockchain-balances-${balance.blockchain}"]`, {
      timeout: 120000
    }).should('not.be.exist');
  }

  confirmDelete() {
    cy.get('[data-cy=confirm-dialog]')
      .find('[data-cy=dialog-title]')
      .should('contain', 'Account delete');
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
  }
}
