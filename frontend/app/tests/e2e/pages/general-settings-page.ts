import { RotkiApp } from './rotki-app';

export class GeneralSettingsPage {
  visit() {
    cy.get('.user-dropdown').click();
    cy.get('[data-cy=user-dropdown]').should('be.visible');
    cy.get('.user-dropdown__settings').click();
    cy.get('[data-cy=user-dropdown]').should('not.be.visible');
    cy.get('a.settings__general').click();
  }

  setFloatingPrecision(value: string) {
    cy.get('.general-settings__fields__floating-precision input').clear();
    cy.get('.general-settings__fields__floating-precision input').type(value);
    cy.get('.general-settings__fields__floating-precision input').blur();
  }

  changeAnonymousUsageStatistics() {
    cy.get('.general-settings__fields__anonymous-usage-statistics').click();
    this.confirmInlineSuccess(
      '.general-settings__fields__anonymous-usage-statistics'
    );
  }

  selectCurrency(value: string) {
    cy.get('.general-settings__fields__currency-selector').click();
    cy.get(`#currency__${value.toLocaleLowerCase()}`).click();
  }

  setBalanceSaveFrequency(value: string) {
    cy.get('.general-settings__fields__balance-save-frequency input').clear();
    cy.get('.general-settings__fields__balance-save-frequency input').type(
      value
    );
    cy.get('.general-settings__fields__balance-save-frequency input').blur();
  }

  setDateDisplayFormat(value: string) {
    cy.get('.general-settings__fields__date-display-format input').clear();
    cy.get('.general-settings__fields__date-display-format input').type(value);
    cy.get('.general-settings__fields__date-display-format input').blur();
  }

  toggleScrambleData() {
    cy.get('.general-settings__fields__scramble-data').click();
  }

  changePassword(currentPassword: string, newPassword: string) {
    cy.get(
      '.general-settings__account-and-security__fields__current-password input'
    ).clear();
    cy.get(
      '.general-settings__account-and-security__fields__current-password input'
    ).type(currentPassword);

    cy.get(
      '.general-settings__account-and-security__fields__new-password input'
    ).clear();
    cy.get(
      '.general-settings__account-and-security__fields__new-password input'
    ).type(newPassword);

    cy.get(
      '.general-settings__account-and-security__fields__new-password-confirm input'
    ).clear();
    cy.get(
      '.general-settings__account-and-security__fields__new-password-confirm input'
    ).type(newPassword);

    cy.get(
      '.general-settings__account-and-security__buttons__change-password'
    ).click();
  }

  confirmInlineSuccess(target: string, messageContains?: string) {
    cy.get(`${target} .v-messages__message`).should(
      'include.text',
      'Setting saved'
    );
    if (messageContains) {
      cy.get(`${target} .v-messages__message`).should(
        'include.text',
        messageContains
      );
    }
  }

  confirmFieldSuccess(target: string, messageContains?: string) {
    cy.get(`${target} .details`).should('include.text', 'Setting saved');
    if (messageContains) {
      cy.get(`${target} .details`).should('include.text', messageContains);
    }
  }

  confirmInlineFailure(target: string, messageContains?: string) {
    cy.get(`${target} .v-messages__message`).should(
      'include.text',
      'Setting not saved'
    );
    if (messageContains) {
      cy.get(`${target} .v-messages__message`).should(
        'include.text',
        messageContains
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
      settings.floatingPrecision
    );
    cy.get('.general-settings__fields__anonymous-usage-statistics input')
      .should('have.attr', 'aria-checked')
      .and('include', `${settings.anonymousUsageStatistics}`);
    cy.get(
      '.general-settings__fields__currency-selector .v-select__selection'
    ).should('have.text', settings.currency);
    cy.get('.general-settings__fields__balance-save-frequency input').should(
      'have.value',
      settings.balanceSaveFrequency
    );
    cy.get('.general-settings__fields__date-display-format input').should(
      'have.value',
      settings.dateDisplayFormat
    );
    cy.get('.general-settings__fields__thousand-separator input').should(
      'have.value',
      settings.thousandSeparator
    );
    cy.get('.general-settings__fields__decimal-separator input').should(
      'have.value',
      settings.decimalSeparator
    );
    cy.get('.general-settings__fields__currency-location input').should(
      'have.length',
      2
    );
    cy.get(
      `.general-settings__fields__currency-location input[aria-checked=true]`
    ).should('have.value', settings.currencyLocation);
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
