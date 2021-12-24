export class HistoryPage {
  visit() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__history').click();
    cy.get('.navigation__history-trades').click();
    cy.get('[data-cy=history-tab]').should('be.visible');
  }
}
