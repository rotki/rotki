import { MODULE_AAVE, MODULES } from '@/services/session/consts';

export class DefiPage {
  visit() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__defi').click();
    cy.get('.navigation__defi-overview').click();
  }

  goToSelectModules() {
    cy.get('.defi-wizard__select-modules').click();
  }

  selectModules() {
    for (let i = 0; i < MODULES.length; i++) {
      const module = MODULES[i];
      if (module === MODULE_AAVE) {
        continue;
      }

      cy.get(`#defi-module-${module}`).scrollIntoView();
      cy.get(`#defi-module-${module}`).find('button').click();
      cy.get(`#defi-module-${module}`).should('not.be.visible');
    }
    cy.get(`#defi-module-${MODULE_AAVE}`).should('be.visible');
    cy.get('.defi-wizard__select-accounts').click();
  }

  selectAccounts() {
    cy.get('.module-address-selector')
      .find('.v-stepper__header')
      .children()
      .should('have.length', 1);
    cy.get('.defi-wizard__done').click();
  }

  defiOverviewIsVisible() {
    cy.contains('Defi Overview').should('be.visible');
  }
}
