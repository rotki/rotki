import { bigNumberify } from '@/utils/bignumbers';

export class AccountBalancesPage {
  getSanitizedAmountString(amount: string) {
    // TODO: extract the `replace(/,/g, '')` as to use user settings (when implemented)
    return amount.replace(/,/g, '');
  }

  formatAmount(amount: string) {
    return bigNumberify(amount).toFormat(2);
  }

  visit() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__accounts-balances').click();
    cy.get('[data-cy=accounts-balances-tab]').scrollIntoView();
    cy.get('[data-cy=accounts-balances-tab]').should('be.visible');
  }
}
