export class GeneralSettingsPage {
  visit() {
    cy.get('.user-dropdown').click();
    cy.get('[data-cy=user-dropdown]').should('be.visible');
    cy.get('.user-dropdown__settings').click();
    cy.get('[data-cy=user-dropdown]').should('not.be.visible');
    cy.get('a.settings__general').click({ force: true });
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

  setHistoryDataStart() {
    cy.get('.general-settings__fields__historic-data-start input').click();
    cy.get('.v-picker__body .v-date-picker-header__value button').click(); // click up to month selection
    cy.get('.v-picker__body .v-date-picker-header__value button')
      .contains(/^2015$/)
      .click(); // clear up to year selection
    cy.get('.v-picker__body .v-date-picker-years li').contains('2018').click();
    cy.get('.v-picker__body .v-date-picker-table--month .v-btn__content')
      .contains('Oct')
      .click();
    cy.get('.v-picker__body .v-date-picker-table--date .v-btn__content')
      .contains('3')
      .click();
  }

  selectCurrency(value: string) {
    cy.get('.general-settings__fields__currency-selector').click();
    cy.get(`#currency__${value.toLocaleLowerCase()}`).click();
  }

  setThousandSeparator(value: string) {
    cy.get('.general-settings__fields__thousand-separator input').clear();
    cy.get('.general-settings__fields__thousand-separator').type(value);
    cy.get('.general-settings__fields__thousand-separator input').blur();
  }

  setDecimalSeparator(value: string) {
    cy.get('.general-settings__fields__decimal-separator input').clear();
    cy.get('.general-settings__fields__decimal-separator').type(value);
    cy.get('.general-settings__fields__decimal-separator input').blur();
  }

  setCurrencyLocation(value: 'after' | 'before') {
    cy.get('.general-settings__fields__currency-location input').clear();
    cy.get('.general-settings__fields__currency-location').type(value);
    cy.get('.general-settings__fields__currency-location input').blur();
  }

  setBalanceSaveFrequency(value: string) {
    cy.get('.general-settings__fields__balance-save-frequency input').clear();
    cy.get('.general-settings__fields__balance-save-frequency').type(value);
    cy.get('.general-settings__fields__balance-save-frequency input').blur();
  }

  setDateDisplayFormat(value: string) {
    cy.get('.general-settings__fields__date-display-format input').clear();
    cy.get('.general-settings__fields__date-display-format').type(value);
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

  saveSettings() {
    cy.get('.general-settings__buttons__save').click();
  }

  confirmSuccess() {
    cy.get('.message-dialog__title').should('include.text', 'Success');
    cy.get('.message-dialog__buttons__confirm').click();
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
    this.verifyRPCEndpoint(settings.rpcEndpoint);
  }

  verifyRPCEndpoint(rpcEndpoint: string) {
    cy.get('.general-settings__fields__rpc-endpoint input').should(
      'have.value',
      rpcEndpoint
    );
  }

  navigateAway() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__dashboard').click();
  }

  setRpcEndpoint(value: string) {
    cy.get('.general-settings__fields__rpc-endpoint input').clear();
    cy.get('.general-settings__fields__rpc-endpoint').type(value);
    cy.get('.general-settings__fields__rpc-endpoint input').blur();
  }

  confirmFailure() {
    cy.get('.message-dialog__title').should('include.text', 'Settings Error');
    cy.get('.message-dialog__buttons__confirm').click();
  }
}
