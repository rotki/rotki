import { RotkiApp } from './rotki-app';

export class RpcSettingsPage {
  visit() {
    cy.get('.user-dropdown').click();
    cy.get('[data-cy=user-dropdown]').should('exist');
    cy.get('.user-dropdown__settings').click();
    cy.get('[data-cy=user-dropdown]').should('not.exist');
    cy.get('a.settings__rpc').click();
  }

  changePassword(currentPassword: string, newPassword: string) {
    cy.get('.general-settings__account-and-security__fields__current-password input').clear();
    cy.get('.general-settings__account-and-security__fields__current-password input').type(currentPassword);

    cy.get('.general-settings__account-and-security__fields__new-password input').clear();
    cy.get('.general-settings__account-and-security__fields__new-password input').type(newPassword);

    cy.get('.general-settings__account-and-security__fields__new-password-confirm input').clear();
    cy.get('.general-settings__account-and-security__fields__new-password-confirm input').type(newPassword);

    cy.get('.general-settings__account-and-security__buttons__change-password').click();
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
