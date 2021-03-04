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
    cy.get('#defi-module-makerdao_dsr').find('button').click();
    cy.get('#defi-module-makerdao_vaults').find('button').click();
    cy.get('#defi-module-compound').find('button').click();
    cy.get('#defi-module-yearn_vaults').find('button').click();
    cy.get('#defi-module-uniswap').find('button').click();
    cy.get('#defi-module-adex').find('button').click();
    cy.get('#defi-module-loopring').find('button').click();
    cy.get('#defi-module-balancer').find('button').click();
    cy.get('#defi-module-aave').should('be.visible');
    cy.get('#defi-module-makerdao_dsr').should('not.be.visible');
    cy.get('#defi-module-makerdao_vaults').should('not.be.visible');
    cy.get('#defi-module-compound').should('not.be.visible');
    cy.get('#defi-module-yearn_vaults').should('not.be.visible');
    cy.get('#defi-module-uniswap').should('not.be.visible');
    cy.get('#defi-module-adex').should('not.be.visible');
    cy.get('#defi-module-loopring').should('not.be.visible');
    cy.get('#defi-module-balancer').should('not.be.visible');
    cy.get('.defi-wizard__select-accounts').click();
  }

  selectAccounts() {
    cy.get('.defi-address-selector')
      .find('.v-stepper__header')
      .children()
      .should('have.length', 1);
    cy.get('.defi-wizard__done').click();
  }

  defiOverviewIsVisible() {
    cy.contains('Defi Overview').should('be.visible');
  }
}
