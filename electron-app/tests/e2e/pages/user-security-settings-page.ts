export class UserSecuritySettingsPage {
  visit() {
    cy.get('.user-dropdown').click();
    cy.get('.user-dropdown__settings').click();
    cy.get('a.settings-usersecurity').click();
  }

  changePassword(currentPassword: string, newPassword: string) {
    cy.get(
      '.settings-general__account-and-security__fields__current-password input'
    ).clear();
    cy.get(
      '.settings-general__account-and-security__fields__current-password input'
    ).type(currentPassword);

    cy.get(
      '.settings-general__account-and-security__fields__new-password input'
    ).clear();
    cy.get(
      '.settings-general__account-and-security__fields__new-password input'
    ).type(newPassword);

    cy.get(
      '.settings-general__account-and-security__fields__new-password-confirm input'
    ).clear();
    cy.get(
      '.settings-general__account-and-security__fields__new-password-confirm input'
    ).type(newPassword);

    cy.get(
      '.settings-general__account-and-security__buttons__change-password'
    ).click();
  }

  confirmSuccess() {
    cy.get('.message-dialog__title').should('include.text', 'Success');
    cy.get('.message-dialog__buttons__confirm').click();
  }

  confirmFailure() {
    cy.get('.message-dialog__title').should('include.text', 'Settings Error');
    cy.get('.message-dialog__buttons__confirm').click();
  }
}
