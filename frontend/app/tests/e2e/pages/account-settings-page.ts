export class AccountSettingsPage {
  visit() {
    cy.get('.user-dropdown').click();
    cy.get('[data-cy=user-dropdown]').should('exist');
    cy.get('.user-dropdown__settings').click();
    cy.get('[data-cy=user-dropdown]').should('not.exist');
    cy.get('a.settings__account').click();
  }

  changePassword(currentPassword: string, newPassword: string) {
    cy.get('.user-security-settings__fields__current-password input').clear();
    cy.get('.user-security-settings__fields__current-password input').type(currentPassword);

    cy.get('.user-security-settings__fields__new-password input').clear();
    cy.get('.user-security-settings__fields__new-password input').type(newPassword);

    cy.get('.user-security-settings__fields__new-password-confirm input').clear();
    cy.get('.user-security-settings__fields__new-password-confirm input').type(newPassword);

    cy.get('.user-security-settings__buttons__change-password').click();
  }

  confirmSuccess() {
    cy.get('[data-cy=message-dialog__title]').should('include.text', 'Success');
    cy.get('[data-cy=message-dialog__ok]').click();
  }
}
