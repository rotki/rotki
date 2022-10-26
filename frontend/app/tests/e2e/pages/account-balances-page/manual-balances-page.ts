import { TradeLocation } from '@/types/history/trade-location';
import { bigNumberify, Zero } from '@/utils/bignumbers';
import { toSentenceCase } from '@/utils/text';
import { AccountBalancesPage } from './index';

export interface FixtureManualBalance {
  readonly asset: string;
  readonly keyword: string;
  readonly label: string;
  readonly amount: string;
  readonly location: TradeLocation;
  readonly tags: string[];
}

export class ManualBalancesPage extends AccountBalancesPage {
  visit() {
    cy.get('.accounts-balances__manual-balances')
      .scrollIntoView()
      .should('be.visible')
      .click();
  }

  addBalance(balance: FixtureManualBalance) {
    cy.get('.big-dialog').should('be.visible');
    cy.get('.manual-balances-form__asset').type(balance.keyword);
    cy.get('[data-cy="no_assets"]').should('not.exist');
    cy.get(`#asset-${balance.asset.toLowerCase()}`).should('be.visible');
    cy.get('.v-autocomplete__content .v-list > div').should($list => {
      expect($list.eq(0)).to.contain(balance.asset);
    });
    cy.get('.manual-balances-form__asset').type('{enter}');
    cy.get('.manual-balances-form__label').type(balance.label);
    cy.get('.manual-balances-form__amount').type(balance.amount);
    for (const tag of balance.tags) {
      cy.get('.manual-balances-form__tags').type(tag).type('{enter}');
    }

    cy.get('.manual-balances-form__location').click();
    cy.get('.manual-balances-form__location').type(`{selectall}{backspace}`);
    cy.get('.manual-balances-form__location').type(balance.location);
    cy.get('.manual-balances-form__location').type('{enter}');
    cy.get('.v-autocomplete__content').should('not.be.visible');
    cy.get('.big-dialog__buttons__confirm').click();
    cy.get('.big-dialog', { timeout: 120000 }).should('not.be.visible');
  }

  visibleEntries(visible: number) {
    // the total row is added to the visible entries
    cy.get('[data-cy="manual-balances"] tbody')
      .find('tr')
      .should('have.length', visible + 1);
  }

  balanceShouldMatch(balances: FixtureManualBalance[]) {
    let i = 0;
    for (const balance of balances) {
      cy.get('[data-cy="manual-balances"] tbody').find('tr').eq(i).as('row');

      cy.get('@row')
        .find('.manual-balances-list__amount')
        .should('contain', this.formatAmount(balance.amount));

      i += 1;
    }
  }

  balanceShouldNotMatch(balances: FixtureManualBalance[]) {
    let i = 0;
    for (const balance of balances) {
      cy.get('[data-cy="manual-balances"] tbody').find('tr').eq(i).as('row');

      cy.get('@row')
        .find('.manual-balances-list__amount')
        .should('not.contain', this.formatAmount(balance.amount));

      i += 1;
    }
  }

  isVisible(position: number, balance: FixtureManualBalance) {
    cy.get('[data-cy="manual-balances"] tbody')
      .find('tr')
      .eq(position)
      .as('row');

    cy.get('@row').find('[data-cy=label]').should('contain', balance.label);

    cy.get('@row')
      .find('.manual-balances-list__amount')
      .should('contain', this.formatAmount(balance.amount));

    cy.get('[data-cy="manual-balances"] thead').scrollIntoView();

    cy.get('@row')
      .find('.manual-balances-list__location')
      .should('contain', toSentenceCase(balance.location));

    cy.get('@row')
      .find('[data-cy=details-symbol]')
      .should('contain.text', balance.asset);

    for (const tag of balance.tags) {
      cy.get('@row').find('.tag').contains(tag).should('be.visible');
    }
  }

  getLocationBalances() {
    const balanceLocations = [
      { location: 'blockchain', renderedValue: Zero },
      { location: 'banks', renderedValue: Zero },
      { location: 'external', renderedValue: Zero },
      { location: 'commodities', renderedValue: Zero },
      { location: 'real estate', renderedValue: Zero },
      { location: 'equities', renderedValue: Zero }
    ];

    balanceLocations.forEach(balanceLocation => {
      const rowClass = `.manual-balance__location__${balanceLocation.location}`;
      cy.get('body').then($body => {
        if ($body.find(rowClass).length > 0) {
          cy.get(`${rowClass} td:nth-child(6) [data-cy="display-amount"]`).each(
            $amount => {
              balanceLocation.renderedValue =
                balanceLocation.renderedValue.plus(
                  bigNumberify(this.getSanitizedAmountString($amount.text()))
                );
            }
          );
        }
      });
    });

    return cy.wrap(balanceLocations);
  }

  editBalance(position: number, amount: string) {
    cy.get('[data-cy="manual-balances"] tbody')
      .find('tr')
      .eq(position)
      .find('button.actions__edit')
      .click();

    cy.get('[data-cy="manual-balance-form"]').as('edit-form');
    cy.get('@edit-form').find('.manual-balances-form__amount input').clear();
    cy.get('@edit-form').find('.manual-balances-form__amount').type(amount);
    cy.get('.big-dialog__buttons__confirm').click();
  }

  deleteBalance(position: number) {
    cy.get('[data-cy="manual-balances"] tbody')
      .find('tr')
      .eq(position)
      .find('button.actions__delete')
      .click();

    this.confirmDelete();
  }

  confirmDelete() {
    cy.get('[data-cy=confirm-dialog]')
      .find('[data-cy=dialog-title]')
      .should('contain', 'Delete manually tracked balance');
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
  }

  showsCurrency(currency: string) {
    cy.get('[data-cy="manual-balances"]')
      .scrollIntoView()
      .contains(`${currency} Value`)
      .should('be.visible');
  }
}
