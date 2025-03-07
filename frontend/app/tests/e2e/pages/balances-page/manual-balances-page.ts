import { BigNumber, toSentenceCase } from '@rotki/common';
import { selectAsset } from '../../support/utils';
import { formatAmount, updateLocationBalance } from '../../utils/amounts';
import { RotkiApp } from '../rotki-app';

export interface FixtureManualBalance {
  readonly asset: string;
  readonly keyword: string;
  readonly label: string;
  readonly amount: string;
  readonly location: string;
  readonly tags: string[];
}

export class ManualBalancesPage {
  visit() {
    RotkiApp.navigateTo('balances', 'balances-manual');
  }

  addBalance(balance: FixtureManualBalance) {
    cy.get('[data-cy=bottom-dialog]').should('be.visible');
    selectAsset('[data-cy=manual-balances-form-asset]', balance.keyword, balance.asset);
    cy.get('[data-cy=manual-balances-form-label]').type(balance.label);
    cy.get('[data-cy=manual-balances-form-amount]').type(balance.amount);
    for (const tag of balance.tags) cy.get('[data-cy=manual-balances-form-tags]').type(`${tag}{enter}`);

    cy.get('[data-cy=manual-balances-form-location]').click();
    cy.get('[data-cy=manual-balances-form-location]').type(balance.location);
    cy.get('[role=menu-content] button').should('have.length', 1);
    cy.get('[data-cy=manual-balances-form-location]').type('{enter}');
    cy.get('[role=menu-content]').should('not.exist');
    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').click();
    cy.get('[data-cy=bottom-dialog]', { timeout: 120000 }).should('not.exist');
    cy.get('[data-cy=price-refresh]').should('not.be.disabled');
  }

  visibleEntries(visible: number) {
    // the total row is added to the visible entries
    cy.get('[data-cy=manual-balances] tbody')
      .find('tr')
      .should('have.length', visible + 1);
  }

  balanceShouldMatch(balances: FixtureManualBalance[]) {
    let i = 0;
    for (const balance of balances) {
      cy.get('[data-cy=manual-balances] tbody').find('tr').eq(i).as('row');

      cy.get('@row').find('[data-cy=manual-balances__amount]').should('contain', formatAmount(balance.amount));

      i += 1;
    }
  }

  balanceShouldNotMatch(balances: FixtureManualBalance[]) {
    let i = 0;
    for (const balance of balances) {
      cy.get('[data-cy=manual-balances] tbody').find('tr').eq(i).as('row');

      cy.get('@row').find('[data-cy=manual-balances__amount]').should('not.contain', formatAmount(balance.amount));
      i += 1;
    }
  }

  isVisible(position: number, balance: FixtureManualBalance) {
    cy.get('[data-cy=manual-balances] tbody').find('tr').eq(position).as('row');

    cy.get('@row').find('[data-cy=label]').should('contain', balance.label);

    cy.get('@row').find('[data-cy=manual-balances__amount]').should('contain', formatAmount(balance.amount));

    cy.get('[data-cy=manual-balances] thead').first().scrollIntoView();

    cy.get('@row').find('[data-cy=manual-balances__location]').should('contain', toSentenceCase(balance.location));

    cy.get('@row').find('[data-cy=list-title]').should('contain.text', balance.asset);

    for (const tag of balance.tags) cy.get('@row').find('.tag').contains(tag).should('be.visible');
  }

  private getLocationBalances() {
    const balances: Map<string, BigNumber> = new Map();

    cy.get('[data-cy=manual-balances__location]').each(($element) => {
      const location = $element.attr('data-location');
      if (!location) {
        cy.log('missing location for element ', $element);
        return true;
      }

      const amount = $element.closest('tr').find('td:nth-child(6) [data-cy=display-amount]').text();
      updateLocationBalance(amount, balances, location);
    });

    return cy.wrap(balances);
  }

  getTotals() {
    return this.getLocationBalances().then(($balances) => {
      let total = new BigNumber(0);
      const balances: { location: string; value: BigNumber }[] = [];

      $balances.forEach((value, location) => {
        total = total.plus(value.toFixed(2, BigNumber.ROUND_DOWN));
        balances.push({ location, value });
      });

      return cy.wrap({
        total,
        balances,
      });
    });
  }

  editBalance(position: number, amount: string) {
    cy.get('[data-cy=manual-balances] tbody')
      .find('tr')
      .eq(position)
      .find('button[data-cy=row-edit]')
      .as('edit-button');

    cy.get('@edit-button').should('be.visible');
    cy.get('@edit-button').should('not.be.disabled');
    cy.get('@edit-button').click();

    cy.get('[data-cy=manual-balance-form]').as('edit-form');
    cy.get('@edit-form').find('[data-cy=manual-balances-form-amount] input').clear();
    cy.get('@edit-form').find('[data-cy=manual-balances-form-amount]').type(amount);
    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').click();
    cy.get('[data-cy=bottom-dialog]', { timeout: 120000 }).should('not.exist');
    cy.get('[data-cy=price-refresh]').should('not.be.disabled');
  }

  deleteBalance(position: number) {
    cy.get('[data-cy=manual-balances] tbody').find('tr').eq(position).find('button[data-cy=row-delete]').click();

    this.confirmDelete();
  }

  confirmDelete() {
    cy.get('[data-cy=confirm-dialog]')
      .find('[data-cy=dialog-title]')
      .should('contain', 'Delete manually tracked balance');
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
  }

  showsCurrency(currency: string) {
    cy.get('[data-cy=manual-balances]').first().scrollIntoView();
    cy.get('[data-cy=manual-balances]').first().contains(`${currency} Value`);
    cy.get('[data-cy=manual-balances]').first().should('be.visible');
  }

  openAddDialog() {
    cy.get('[data-cy=manual-balances-add-button]').should('be.visible');
    cy.get('[data-cy=manual-balances-add-button]').should('not.be.disabled');
    cy.get('[data-cy=manual-balances-add-button]').click();
  }
}
