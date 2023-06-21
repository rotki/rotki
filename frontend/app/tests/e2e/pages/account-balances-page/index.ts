import { RotkiApp } from '../rotki-app';

export class AccountBalancesPage {
  getSanitizedAmountString(amount: string) {
    // TODO: extract the `replace(/,/g, '')` as to use user settings (when implemented)
    return amount.replace(/,/g, '');
  }

  formatAmount(amount: string) {
    return bigNumberify(amount).toFormat(2);
  }

  visit() {
    RotkiApp.navigateTo('accounts-balances');
    cy.get('[data-cy=accounts-balances-tab]').should('be.visible');
  }
}
