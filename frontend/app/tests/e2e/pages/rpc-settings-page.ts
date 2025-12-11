import { RotkiApp } from './rotki-app';

export class RpcSettingsPage {
  visit() {
    cy.get('[data-cy=user-menu-button]').click();
    cy.get('[data-cy=user-dropdown]').should('exist');
    cy.get('[data-cy=settings-button]').click();
    cy.get('[data-cy=user-dropdown]').should('not.exist');
    cy.get('[data-cy="settings__rpc"]').click();
  }

  changePassword(currentPassword: string, newPassword: string) {
    cy.get('[data-cy=current-password-input]').clear();
    cy.get('[data-cy=current-password-input]').type(currentPassword);
    cy.get('[data-cy=new-password-input]').clear();
    cy.get('[data-cy=new-password-input]').type(newPassword);
    cy.get('[data-cy=confirm-password-input]').clear();
    cy.get('[data-cy=confirm-password-input]').type(newPassword);
    cy.get('[data-cy=change-password-button]').click();
  }

  confirmInlineSuccess(target: string, messageContains?: string) {
    cy.confirmFieldMessage({ target, messageContains, mustInclude: 'Setting saved' });
  }

  navigateAway() {
    RotkiApp.navigateTo('dashboard');
  }

  addEthereumRPC(name: string, endpoint: string) {
    cy.get('[data-cy=add-node]').click();
    cy.get('[data-cy=bottom-dialog]').should('be.visible');
    cy.get('[data-cy=node-name]').type(name);
    cy.get('[data-cy=node-endpoint]').type(endpoint);
    cy.get('[data-cy=confirm]').click();
    cy.get('[data-cy=bottom-dialog]').should('not.exist');
  }

  confirmRPCAddition(name: string, endpoint: string) {
    cy.get('[data-cy=ethereum-node]').children().should('contain.text', name);
    cy.get('[data-cy=ethereum-node]').children().should('contain.text', endpoint);
  }

  confirmRPCmissing(name: string, endpoint: string) {
    cy.get('[data-cy=ethereum-node]').children().should('not.contain.text', name);
    cy.get('[data-cy=ethereum-node]').children().should('not.contain.text', endpoint);
  }
}
