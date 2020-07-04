import axios from 'axios';
import { ActionResult } from '../../../src/model/action-result';

export class RotkiApp {
  visit() {
    cy.visit('/');
  }

  createAccount(username: string, password: string = '1234') {
    // simulate high scaling / low res by making a very small viewpoirt
    cy.get('.login__button__new-account').click();
    cy.get('.create-account__fields__username').type(username);
    cy.get('.create-account__fields__password').type(password);
    cy.get('.create-account__fields__password-repeat').type(password);
    cy.get('.create-account__buttons__confirm').click();
  }

  closePremiumOverlay() {
    cy.get('.account-management__premium_dialog__title', {
      timeout: 10000
    }).should('include.text', 'Upgrade to Premium');
    cy.get('.account-management__premium_dialog__buttons__cancel').click();
    cy.get('.account-management__premium_dialog').should('not.be.visible');
  }

  login(username: string, password: string = '1234') {
    cy.get('.login__fields__username').type(username);
    cy.get('.login__fields__password').type(password);
    cy.get('.login__button__sign-in').click();
  }

  logout() {
    cy.get('.user-dropdown').click();
    cy.get('.user-dropdown__logout').click();
    cy.get('.confirm-dialog__buttons__confirm').click();
    cy.get('.login__fields__username').should('be.visible');
  }

  changeCurrency(currency: string) {
    cy.get('.currency-dropdown').click();
    cy.get(`#change-to-${currency.toLocaleLowerCase()}`).click();
  }

  togglePrivacyMode() {
    cy.get('.user-dropdown').click();
    cy.get('.user-dropdown__privacy-mode').click();
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
