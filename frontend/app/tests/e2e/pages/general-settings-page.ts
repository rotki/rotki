export class GeneralSettingsPage {
  visit() {
    cy.get('.user-dropdown').click();
    cy.get('.user-dropdown__settings').click();
    cy.get('a.settings-general').click();
  }

  setFloatingPrecision(value: string) {
    cy.get('.settings-general__fields__floating-precision input').clear();
    cy.get('.settings-general__fields__floating-precision input').type(value);
    cy.get('.settings-general__fields__floating-precision input').blur();
  }

  changeAnonymizedLogs() {
    cy.get('.settings-general__fields__anonymized-logs').click();
    this.confirmInlineSuccess('.settings-general__fields__anonymized-logs');
  }

  changeAnonymousUsageStatistics() {
    cy.get('.settings-general__fields__anonymous-usage-statistics').click();
    this.confirmInlineSuccess(
      '.settings-general__fields__anonymous-usage-statistics'
    );
  }

  setHistoryDataStart() {
    cy.get('.settings-general__fields__historic-data-start input').click();
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
    cy.get('.settings-general__fields__currency-selector').click();
    cy.get(`#currency__${value.toLocaleLowerCase()}`).click();
  }

  setBalanceSaveFrequency(value: string) {
    cy.get('.settings-general__fields__balance-save-frequency input').clear();
    cy.get('.settings-general__fields__balance-save-frequency').type(value);
    cy.get('.settings-general__fields__balance-save-frequency input').blur();
  }

  setDateDisplayFormat(value: string) {
    cy.get('.settings-general__fields__date-display-format input').clear();
    cy.get('.settings-general__fields__date-display-format').type(value);
    cy.get('.settings-general__fields__date-display-format input').blur();
  }

  toggleScrambleData() {
    cy.get('.settings-general__fields__scramble-data').click();
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

  saveSettings() {
    cy.get('.settings-general__buttons__save').click();
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
    anonymizedLogs: boolean;
    anonymousUsageStatistics: boolean;
    floatingPrecision: string;
    dateDisplayFormat: string;
    currency: string;
    balanceSaveFrequency: string;
    historicDataStart: string;
    rpcEndpoint: string;
  }) {
    cy.get('.settings-general__fields__floating-precision input').should(
      'have.value',
      settings.floatingPrecision
    );
    cy.get('.settings-general__fields__anonymized-logs input')
      .should('have.attr', 'aria-checked')
      .and('include', `${settings.anonymizedLogs}`);
    cy.get('.settings-general__fields__anonymous-usage-statistics input')
      .should('have.attr', 'aria-checked')
      .and('include', `${settings.anonymousUsageStatistics}`);
    cy.get('.settings-general__fields__historic-data-start input').should(
      'have.value',
      settings.historicDataStart
    );
    cy.get(
      '.settings-general__fields__currency-selector .v-select__selection'
    ).should('have.text', settings.currency);
    cy.get('.settings-general__fields__balance-save-frequency input').should(
      'have.value',
      settings.balanceSaveFrequency
    );
    cy.get('.settings-general__fields__date-display-format input').should(
      'have.value',
      settings.dateDisplayFormat
    );
    this.verifyRPCEndpoint(settings.rpcEndpoint);
  }

  verifyRPCEndpoint(rpcEndpoint: string) {
    cy.get('.settings-general__fields__rpc-endpoint input').should(
      'have.value',
      rpcEndpoint
    );
  }

  navigateAway() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__otc-trades').click();
  }

  setRpcEndpoint(value: string) {
    cy.get('.settings-general__fields__rpc-endpoint input').clear();
    cy.get('.settings-general__fields__rpc-endpoint').type(value);
    cy.get('.settings-general__fields__rpc-endpoint input').blur();
  }

  confirmFailure() {
    cy.get('.message-dialog__title').should('include.text', 'Settings Error');
    cy.get('.message-dialog__buttons__confirm').click();
  }
}
