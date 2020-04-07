import axios from 'axios';
import { ActionResult } from '../../../src/model/action-result';

export class RotkiApp {
  visit() {
    cy.visit('/');
  }

  createAccount(username: string) {
    cy.get('.login__button__new-account').click();
    cy.get('.create-account__fields__username').type(username);
    cy.get('.create-account__fields__password').type('1234');
    cy.get('.create-account__fields__password-repeat').type('1234');
    cy.get('.create-account__buttons__confirm').click();
  }

  closePremiumOverlay() {
    cy.contains(
      '.account_management__premium .message-overlay__title',
      'Upgrade to Premium'
    );
    cy.get('.message-overlay__buttons__cancel').click();
  }

  login(username: string) {
    cy.get('.login__fields__username').type(username);
    cy.get('.login__fields__password').type('1234');
    cy.get('.login__button__sign-in').click();
  }

  logout() {
    cy.get('.user-dropdown').click();
    cy.get('.user-dropdown__logout').click();
    cy.get('.confirm-dialog__buttons__confirm').click();
  }

  logoutApi(username: string, cb: () => void) {
    axios
      .create({
        baseURL: `http://localhost:4242/api/1/`,
        timeout: 30000
      })
      .patch<ActionResult<boolean>>(`/users/${username}`, {
        action: 'logout'
      })
      .then(() => cb())
      .catch(() => cb());
  }
}
