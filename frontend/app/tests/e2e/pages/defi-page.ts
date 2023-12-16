import { RotkiApp } from './rotki-app';

export class DefiPage {
  visit() {
    RotkiApp.navigateTo('defi', 'defi-overview');
  }

  goToSelectModules() {
    cy.get('.defi-wizard__select-modules').click();
  }

  selectModules() {
    cy.get('[data-cy=aave-module-switch] input').should('be.checked');
    cy.get('[data-cy=modules_disable_all').click();
    cy.get('[data-cy=aave-module-switch] input').should('not.be.checked');
    cy.get('[data-cy=aave-module-switch] input').click();
    cy.get('[data-cy=aave-module-switch] input').should('be.checked');
    cy.get('[data-cy=defi-wizard-done]').click();
  }

  defiOverviewIsVisible() {
    cy.contains('Defi Overview').should('be.visible');
  }
}
