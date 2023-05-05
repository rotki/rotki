import { RotkiApp } from '../rotki-app';

export class HistoryPage {
  visit() {
    RotkiApp.navigateMenu('history', 'history-trades');
    cy.get('[data-cy=history-tab]').should('be.visible');
  }
}
