import { RotkiApp } from './rotki-app';

export class GeneralSettingsPage {
  visit() {
    cy.get('.user-dropdown').click();
    cy.get('[data-cy=user-dropdown]').should('be.visible');
    cy.get('.user-dropdown__settings').click();
    cy.get('[data-cy=user-dropdown]').should('not.be.visible');
    cy.get('a.settings__general').click();
  }

  setInputFieldValue(selector: string, value: string) {
    cy.get(selector).as('input');
    cy.get('@input').clear();
    cy.get('@input').type(value);
    cy.get('@input').blur();
  }

  setFloatingPrecision(value: string) {
    this.setInputFieldValue(
      '.general-settings__fields__floating-precision input',
      value,
    );
  }

  changeAnonymousUsageStatistics() {
    cy.get('.general-settings__fields__anonymous-usage-statistics input').click();
    this.confirmInlineSuccess(
      '.general-settings__fields__anonymous-usage-statistics .details .text-rui-success',
    );
  }

  selectCurrency(value: string) {
    cy.get('.general-settings__fields__currency-selector').click();
    cy.get(`#currency__${value.toLocaleLowerCase()}`).click();
  }

  setBalanceSaveFrequency(value: string) {
    this.setInputFieldValue(
      '.general-settings__fields__balance-save-frequency input',
      value,
    );
  }

  setDateDisplayFormat(value: string) {
    this.setInputFieldValue(
      '.general-settings__fields__date-display-format input',
      value,
    );
  }

  toggleScrambleData() {
    cy.get('.general-settings__fields__scramble-data').click();
  }

  changePassword(currentPassword: string, newPassword: string) {
    cy.get(
      '.general-settings__account-and-security__fields__current-password input',
    ).clear();
    cy.get(
      '.general-settings__account-and-security__fields__current-password input',
    ).type(currentPassword);

    cy.get(
      '.general-settings__account-and-security__fields__new-password input',
    ).clear();
    cy.get(
      '.general-settings__account-and-security__fields__new-password input',
    ).type(newPassword);

    cy.get(
      '.general-settings__account-and-security__fields__new-password-confirm input',
    ).clear();
    cy.get(
      '.general-settings__account-and-security__fields__new-password-confirm input',
    ).type(newPassword);

    cy.get(
      '.general-settings__account-and-security__buttons__change-password',
    ).click();
  }

  confirmInlineSuccess(target: string, messageContains?: string) {
    cy.get(target).as('message');
    cy.get('@message').should('include.text', 'Setting saved');
    if (messageContains)
      cy.get('@message').should('include.text', messageContains);
  }

  confirmInlineFailure(target: string, messageContains?: string) {
    cy.get(`${target} .v-messages__message`).should(
      'include.text',
      'Setting not saved',
    );
    if (messageContains) {
      cy.get(`${target} .v-messages__message`).should(
        'include.text',
        messageContains,
      );
    }
  }

  verify(settings: {
    anonymousUsageStatistics: boolean;
    floatingPrecision: string;
    dateDisplayFormat: string;
    thousandSeparator: string;
    decimalSeparator: string;
    currencyLocation: 'after' | 'before';
    currency: string;
    balanceSaveFrequency: string;
    rpcEndpoint: string;
  }) {
    cy.get('.general-settings__fields__floating-precision input').should(
      'have.value',
      settings.floatingPrecision,
    );
    cy.get('.general-settings__fields__anonymous-usage-statistics input')
      .should(settings.anonymousUsageStatistics ? 'be.checked' : 'not.be.checked');
    cy.get(
      '.general-settings__fields__currency-selector .v-select__selection',
    ).should('have.text', settings.currency);
    cy.get('.general-settings__fields__balance-save-frequency input').should(
      'have.value',
      settings.balanceSaveFrequency,
    );
    cy.get('.general-settings__fields__date-display-format input').should(
      'have.value',
      settings.dateDisplayFormat,
    );
    cy.get('.general-settings__fields__thousand-separator input').should(
      'have.value',
      settings.thousandSeparator,
    );
    cy.get('.general-settings__fields__decimal-separator input').should(
      'have.value',
      settings.decimalSeparator,
    );
    cy.get('.general-settings__fields__currency-location input').should(
      'have.length',
      2,
    );
    cy.get(`.general-settings__fields__currency-location input:checked`).should(
      'have.value',
      settings.currencyLocation,
    );
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
    cy.get('[data-cy=bottom-dialog]').should('not.be.visible');
  }

  confirmRPCAddition(name: string, endpoint: string) {
    cy.get('[data-cy=ethereum-node]').children().should('contain.text', name);
    cy.get('[data-cy=ethereum-node]')
      .children()
      .should('contain.text', endpoint);
  }

  confirmRPCmissing(name: string, endpoint: string) {
    cy.get('[data-cy=ethereum-node]')
      .children()
      .should('not.contain.text', name);
    cy.get('[data-cy=ethereum-node]')
      .children()
      .should('not.contain.text', endpoint);
  }
}
