export class AccountSettingsPage {
  visit() {
    cy.get('[data-cy=user-menu-button]').click();
    cy.get('[data-cy=user-dropdown]').should('exist');
    cy.get('[data-cy=settings-button]').click();
    cy.get('[data-cy=user-dropdown]').should('not.exist');
    cy.get('[data-cy="settings__account"]').click();
  }

  changePassword(currentPassword: string, newPassword: string) {
    cy.get('[data-cy=current-password] input').clear();
    cy.get('[data-cy=current-password] input').type(currentPassword);
    cy.get('[data-cy=new-password] input').clear();
    cy.get('[data-cy=new-password] input').type(newPassword);
    cy.get('[data-cy=confirm-password] input').clear();
    cy.get('[data-cy=confirm-password] input').type(newPassword);
    cy.get('[data-cy=change-password-button]').click();
  }

  confirmSuccess() {
    cy.get('[data-cy=message-dialog__title]').should('include.text', 'Success');
    cy.get('[data-cy=message-dialog__ok]').click();
  }
}
