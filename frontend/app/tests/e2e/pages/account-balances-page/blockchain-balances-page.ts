import { Blockchain } from '@rotki/common/lib/blockchain';
import { BigNumber } from '@rotki/common';
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

  isGroupped(balance: FixtureBlockchainBalance) {
    return balance.blockchain === Blockchain.ETH;
  }

  addBalance(balance: FixtureBlockchainBalance) {
    cy.get('[data-cy=bottom-dialog]').should('be.visible');
    cy.get('[data-cy="blockchain-balance-form"]').should('be.visible');
    cy.get('[data-cy="account-blockchain-field"]').type(
      `{selectall}{backspace}${balance.chainName}`,
    );
    cy.get('[data-cy="account-blockchain-field"]').type('{enter}');
    cy.get('[data-cy="input-mode-manual"]').click();

    if (balance.blockchain === Blockchain.ETH)
      setCheckBox('[data-cy="account-all-evm-chains"]', false);

    cy.get('[data-cy="account-address-field"]').should('not.be.disabled');
    cy.get('[data-cy="account-address-field"]').type(balance.address);
    cy.get('[data-cy="account-label-field"]').type(balance.label);

    for (const tag of balance.tags)
      cy.get('[data-cy="account-tag-field"]').type(`${tag}{enter}`);

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

    cy.get('[data-cy=bottom-dialog]', { timeout: 120000 }).should(
      'not.exist',
    );
  }

  isEntryVisible(position: number, balance: FixtureBlockchainBalance) {
    // account balances card section for particular blockchain type should be visible
    // sometime the table need long time to be loaded
    cy.get(`[data-cy=account-table][data-location=${balance.blockchain}]`, {
      timeout: 120000,
    }).as('blockchain-section');

    cy.get('@blockchain-section').should('exist');
    cy.get('@blockchain-section')
      .get('tbody td div[role=progressbar]', { timeout: 300000 })
      .should('not.exist');

    cy.get('@blockchain-section')
      .find('tbody')
      .find('tr')
      .eq(position + (this.isGroupped(balance) ? 0 : 1))
      .as('row');

    cy.get('@row')
      .find('[data-cy="labeled-address-display"]')
      .as('address-label');
    cy.get('@address-label').scrollIntoView();
    cy.get('@address-label').trigger('mouseover');

    cy.get('div[role=tooltip').as('address-tooltip');

    cy.get('@address-tooltip')
      .find('div[role=tooltip-content]')
      .contains(balance.label);
    cy.get('@address-tooltip')
      .find('div[role=tooltip-content]')
      .contains(balance.address);

    for (const tag of balance.tags)
      cy.get('@row').find('.tag').contains(tag).should('be.visible');

    cy.get('@row')
      .find('[data-cy="labeled-address-display"]')
      .as('address-label');
    cy.get('@address-label').scrollIntoView();
    cy.get('@address-label').trigger('mouseleave');
  }

  private getBalances() {
    const balances: Map<string, BigNumber> = new Map();

    cy.get(
      '[data-cy=blockchain-asset-balances] > tbody > [class*=_tr__empty]',
      {
        timeout: 300000,
      },
    ).should('not.exist');

    cy.get('[data-cy=account-table]').each($element =>
      this.updateTableBalance($element, balances),
    );

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

  private updateTableBalance(
    $element: JQuery<HTMLElement>,
    balances: Map<string, BigNumber>,
  ) {
    const blockchain = $element.attr('data-location');

    if (!blockchain) {
      cy.log('missing blockchain');
      return true;
    }

    cy.wrap($element.find('> div > table')).as(`${blockchain}-table`);
    cy.get(`@${blockchain}-table`).scrollIntoView();
    cy.get(`@${blockchain}-table`)
      .find('> tbody > tr > td div[role=progressbar]', {
        timeout: 240000,
      })
      .should('not.exist');

    cy.get(`@${blockchain}-table`)
      .find(
        `> tbody > tr:contains(${blockchain.toUpperCase()}) > td:nth-child(4) [data-cy="display-amount"]`,
      )
      .then((el) => {
        updateLocationBalance(el.text(), balances, blockchain);
      });
  }

  editBalance(
    balance: FixtureBlockchainBalance,
    position: number,
    label: string,
  ) {
    cy.get(`[data-cy=account-table][data-location=${balance.blockchain}] tbody`)
      .find('tr')
      .eq(position + (this.isGroupped(balance) ? 0 : 1))
      .find('button[data-cy="row-edit"]')
      .click();

    cy.get('[data-cy="blockchain-balance-form"]').as('edit-form');
    cy.get('@edit-form')
      .find('[data-cy="account-label-field"]')
      .as('account-label');
    cy.get('@account-label').click();
    cy.get('@account-label').clear();
    cy.get('@account-label').type(label);
    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').click();
    cy.get('[data-cy=bottom-dialog]', { timeout: 120000 }).should(
      'not.exist',
    );
  }

  deleteBalance(balance: FixtureBlockchainBalance, position: number) {
    cy.get(`[data-cy=account-table][data-location=${balance.blockchain}] tbody`)
      .find('tr')
      .eq(position + (this.isGroupped(balance) ? 0 : 1))
      .find('[data-cy*=table-toggle-check-] input[type=checkbox]')
      .click();

    cy.get(`[data-cy=account-balances][data-location=${balance.blockchain}]`)
      .find('[data-cy="account-balances__delete-button"]')
      .click();

    this.confirmDelete();

    cy.get(`[data-cy=account-table][data-location=${balance.blockchain}]`, {
      timeout: 120000,
    }).should('not.exist');
  }

  confirmDelete() {
    cy.get('[data-cy=confirm-dialog]')
      .find('[data-cy=dialog-title]')
      .should('contain', 'Account delete');
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
  }
}
