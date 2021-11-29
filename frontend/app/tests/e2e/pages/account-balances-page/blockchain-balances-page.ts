import { Blockchain } from '@rotki/common/lib/blockchain';
import { bigNumberify, Zero } from '@/utils/bignumbers';
import { AccountBalancesPage } from './index';

export interface FixtureBlockchainBalance {
  readonly blockchain: Blockchain;
  readonly inputMode: string;
  readonly address: string;
  readonly label: string;
  readonly tags: string[];
}

export class BlockchainBalancesPage extends AccountBalancesPage {
  visit() {
    cy.get('.accounts-balances__blockchain-balances')
      .scrollIntoView()
      .should('be.visible')
      .click({
        force: true
      });
  }

  isGroupped(balance: FixtureBlockchainBalance) {
    return balance.blockchain === Blockchain.ETH;
  }

  addBalance(balance: FixtureBlockchainBalance) {
    cy.get('.big-dialog').should('be.visible');
    cy.get('[data-cy="blockchain-balance-form"]').should('be.visible');
    cy.get('[data-cy="account-blockchain-field"]').parent().click();
    cy.get('.v-menu__content').contains(balance.blockchain).click();
    cy.get('[data-cy="input-mode-manual"]').click();
    cy.get('[data-cy="account-address-field"]').type(balance.address);
    cy.get('[data-cy="account-label-field"]').type(balance.label);

    for (const tag of balance.tags) {
      cy.get('[data-cy="account-tag-field"]').type(tag).type('{enter}');
    }

    cy.get('.big-dialog__buttons__confirm').click();
    cy.get('.big-dialog', { timeout: 45000 }).should('not.be.visible');
  }

  isEntryVisible(position: number, balance: FixtureBlockchainBalance) {
    // account balances card section for particular blockchain type should be visible
    // sometime the table need long time to be loaded
    cy.get(`[data-cy="blockchain-balances-${balance.blockchain}"]`, {
      timeout: 300000
    }).as('blockchain-section');

    cy.get('@blockchain-section').should('exist');

    cy.get('@blockchain-section')
      .find('[data-cy="blockchain-balances"] tbody')
      .find('tr')
      .eq(position + (this.isGroupped(balance) ? 0 : 1))
      .as('row');

    cy.get('@row')
      .find('[data-cy="labeled-address-display"]')
      .scrollIntoView()
      .trigger('mouseenter');

    cy.get('.v-tooltip__content.menuable__content__active').as(
      'address-tooltip'
    );

    cy.get('@address-tooltip')
      .find('span:nth-child(1)')
      .contains(balance.label);
    cy.get('@address-tooltip')
      .find('span:nth-child(2)')
      .contains(balance.address);

    cy.get('@row')
      .find('[data-cy="labeled-address-display"]')
      .scrollIntoView()
      .trigger('mouseleave');
  }

  getBlockchainBalances() {
    const blockchainBalances = [
      { blockchain: Blockchain.ETH, renderedValue: Zero },
      { blockchain: Blockchain.BTC, renderedValue: Zero }
    ];

    blockchainBalances.forEach(blockchainBalance => {
      cy.get(
        `[data-cy="blockchain-balances-${blockchainBalance.blockchain}"] tr`
      ).then($rows => {
        if ($rows.text().includes(blockchainBalance.blockchain)) {
          cy.get(
            `[data-cy="blockchain-balances-${blockchainBalance.blockchain}"] tbody tr:contains(${blockchainBalance.blockchain})`
          ).each($row => {
            // loops over all blockchain asset balances rows and adds up the total per blockchain type
            cy.wrap($row)
              .find(
                ':nth-child(4) > .amount-display > .v-skeleton-loader .amount-display__value'
              )
              .then($amount => {
                if (blockchainBalance.renderedValue === Zero) {
                  blockchainBalance.renderedValue = bigNumberify(
                    this.getSanitizedAmountString($amount.text())
                  );
                } else {
                  blockchainBalance.renderedValue =
                    blockchainBalance.renderedValue.plus(
                      bigNumberify(
                        this.getSanitizedAmountString($amount.text())
                      )
                    );
                }
              });
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
      .find('button.account-balances-list__actions__edit')
      .click();

    cy.get('[data-cy="blockchain-balance-form"]').as('edit-form');
    cy.get('@edit-form')
      .find('[data-cy="account-label-field"]')
      .click()
      .clear()
      .type(label);
    cy.get('.big-dialog__buttons__confirm').click();
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

    cy.get(`[data-cy="blockchain-balances-${balance.blockchain}"]`).should(
      'not.be.exist'
    );
  }

  confirmDelete() {
    cy.get('[data-cy=confirm-dialog]')
      .find('[data-cy=dialog-title]')
      .should('contain', 'Account delete');
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
  }
}
