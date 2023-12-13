import { RotkiApp } from './rotki-app';

export class DefiPage {
  visit() {
    RotkiApp.navigateTo('defi', 'defi-overview');
  }

  goToSelectModules() {
    cy.get('.defi-wizard__select-modules').click();
  }

  selectModules() {
    cy.get('[data-cy=aave-module-switch]').should(
      'have.attr',
      'aria-checked',
      'true'
    );
    cy.get('[data-cy=modules_disable_all').click();
    cy.get('[data-cy=aave-module-switch]').should(
      'have.attr',
      'aria-checked',
      'false'
    );
    cy.get('[data-cy=aave-module-switch]').closest('.v-input--switch').click();
    cy.get('[data-cy=aave-module-switch]').should(
      'have.attr',
      'aria-checked',
      'true'
    );
    cy.get('[data-cy=defi-wizard-done]').click();
  }

  defiOverviewIsVisible() {
    cy.contains('Defi Overview').should('be.visible');
  }
}
