import { capitalize } from '@/filters';
import { TradeLocation } from '@/services/history/types';
import { bigNumberify, Zero } from '@/utils/bignumbers';

function formatAmount(amount: string) {
  return bigNumberify(amount).toFormat(2);
}

export interface FixtureManualBalance {
  readonly asset: string;
  readonly keyword: string;
  readonly label: string;
  readonly amount: string;
  readonly location: TradeLocation;
  readonly tags: string[];
}

export class AccountBalancesPage {
  visit() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__accounts-balances').click();
    cy.get('[data-cy=accounts-balances]').should('be.visible');
  }

  addBalance(balances: FixtureManualBalance) {
    cy.get('.big-dialog').should('be.visible');
    cy.get('.manual-balances-form__asset').type(balances.keyword);
    cy.get(`#asset-${balances.asset.toLocaleLowerCase()}`).click();
    cy.get('.manual-balances-form__label').type(balances.label);
    cy.get('.manual-balances-form__amount').type(balances.amount);
    for (const tag of balances.tags) {
      cy.get('.manual-balances-form__tags').type(tag).type('{enter}');
    }
    cy.get('.manual-balances-form__location').click();
    cy.get(
      '.manual-balances-form__location div.v-select__selections input'
    ).type(`{selectall}{backspace}${balances.location}{enter}`);
    cy.get('.big-dialog__buttons__confirm').click();
    cy.get('.big-dialog', { timeout: 45000 }).should('not.be.visible');
  }

  visibleEntries(visible: number) {
    // the total row is added to the visible entries
    cy.get('.manual-balances-list tbody')
      .find('tr')
      .should('have.length', visible + 1);
  }

  balanceShouldMatch(balances: FixtureManualBalance[]) {
    let i = 0;
    for (const balance of balances) {
      cy.get('.manual-balances-list tbody').find('tr').eq(i).as('row');

      cy.get('@row')
        .find('.manual-balances-list__amount')
        .should('contain', formatAmount(balance.amount));

      i += 1;
    }
  }

  balanceShouldNotMatch(balances: FixtureManualBalance[]) {
    let i = 0;
    for (const balance of balances) {
      cy.get('.manual-balances-list tbody').find('tr').eq(i).as('row');

      cy.get('@row')
        .find('.manual-balances-list__amount')
        .should('not.contain', formatAmount(balance.amount));

      i += 1;
    }
  }

  isVisible(position: number, balance: FixtureManualBalance) {
    cy.get('.manual-balances-list tbody').find('tr').eq(position).as('row');

    cy.get('@row')
      .find('.manual-balances-list__label')
      .should('contain', balance.label);

    cy.get('@row')
      .find('.manual-balances-list__amount')
      .should('contain', formatAmount(balance.amount));

    cy.get('.manual-balances-list thead').scrollIntoView();

    cy.get('@row')
      .find('.manual-balances-list__location')
      .should('contain', capitalize(balance.location));

    cy.get('@row')
      .find('[data-cy=details-symbol]')
      .should('contain.text', balance.asset);

    for (const tag of balance.tags) {
      cy.get('@row').find('.tag').contains(tag).should('be.visible');
    }
  }

  getLocationBalances() {
    const balanceLocations = [
      { location: 'Blockchain', renderedValue: Zero },
      { location: 'Banks', renderedValue: Zero },
      { location: 'External', renderedValue: Zero },
      { location: 'Commodities', renderedValue: Zero },
      { location: 'Real estate', renderedValue: Zero },
      { location: 'Equities', renderedValue: Zero }
    ];

    balanceLocations.forEach(balanceLocation => {
      cy.get('.manual-balances-list tr').then($rows => {
        if ($rows.text().includes(balanceLocation.location)) {
          cy.get(
            `.manual-balances-list tr:contains(${balanceLocation.location})`
          ).each($row => {
            // loops over all manual balances rows and adds up the total per location
            // TODO: extract the replace(',', '') as to use user settings (when implemented)
            cy.wrap($row)
              .find(
                ':nth-child(5) > .amount-display > .v-skeleton-loader .amount-display__value'
              )
              .then($amount => {
                if (balanceLocation.renderedValue === Zero) {
                  balanceLocation.renderedValue = bigNumberify(
                    $amount.text().replace(',', '')
                  );
                } else {
                  balanceLocation.renderedValue =
                    balanceLocation.renderedValue.plus(
                      bigNumberify($amount.text().replace(',', ''))
                    );
                }
              });
          });
        }
      });
    });

    return cy.wrap(balanceLocations);
  }

  amountDisplayIsBlurred() {
    cy.get('.amount-display').should('have.class', 'blur-content');
  }

  amountDisplayIsNotBlurred() {
    cy.get('.amount-display').should('not.have.class', 'blur-content');
  }

  editBalance(position: number, amount: string) {
    cy.get('.manual-balances-list tbody')
      .find('tr')
      .eq(position)
      .find('button.manual-balances-list__actions__edit')
      .click();

    cy.get('.manual-balances-form').as('edit-form');
    cy.get('@edit-form').find('.manual-balances-form__amount input').clear();
    cy.get('@edit-form').find('.manual-balances-form__amount').type(amount);
    cy.get('.big-dialog__buttons__confirm').click();
  }

  deleteBalance(position: number) {
    cy.get('.manual-balances-list tbody')
      .find('tr')
      .eq(position)
      .find('.manual-balances-list__actions__delete')
      .click();
  }

  confirmDelete() {
    cy.get('.confirm-dialog__title').should(
      'contain',
      'Delete manually tracked balance'
    );
    cy.get('.confirm-dialog__buttons__confirm').click();
  }

  showsCurrency(currency: string) {
    cy.get('.manual-balances-list')
      .scrollIntoView()
      .contains(`${currency} Value`)
      .should('be.visible');
  }
}
