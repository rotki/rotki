export class AccountingSettingsPage {
  visit() {
    cy.get('.user-dropdown').click();
    cy.get('[data-cy=user-dropdown]').should('be.visible');
    cy.get('.user-dropdown__settings').click();
    cy.get('a.settings__accounting').click({ force: true });
    cy.get('[data-cy=user-dropdown]').should('not.be.visible');
  }

  setTaxFreePeriodDays(value: string) {
    cy.get('.accounting-settings__taxfree-period-days input').clear();
    cy.get('.accounting-settings__taxfree-period-days input').type(value);
    cy.get('.accounting-settings__taxfree-period-days input').blur();
    this.confirmInlineSuccess(
      '.accounting-settings__taxfree-period-days',
      value
    );
  }

  changeSwitch(target: string) {
    cy.get(`${target} input`).then($switch => {
      const initialValue = $switch.attr('aria-checked');
      cy.get(target)
        .click()
        .then(() => {
          expect($switch.attr('aria-checked')).not.to.eq(initialValue);
        });
    });
    this.confirmInlineSuccess(target);
  }

  verifySwitchState(target: string, state: string) {
    cy.get(`${target} input`).then($el => {
      expect($el.attr('aria-checked')).eq(state);
    });
  }

  addIgnoredAsset(asset: string) {
    cy.get(
      '.accounting-settings__asset-to-ignore div.v-select__selections input'
    ).click();
    cy.get(
      '.accounting-settings__asset-to-ignore div.v-select__selections input'
    ).type(`{selectall}{backspace}${asset}{enter}`);
    cy.get('.accounting-settings__buttons__add').click();
  }

  remIgnoredAsset(asset: string) {
    cy.get(
      '.accounting-settings__ignored-assets div.v-select__selections input'
    ).click();
    cy.get(
      '.accounting-settings__ignored-assets div.v-select__selections input'
    ).type(`${asset}{enter}`);
    cy.get('.accounting-settings__buttons__remove').click();
  }

  ignoredAssetCount(number: string) {
    cy.get('.accounting-settings__ignored-assets__badge').should(
      'include.text',
      number
    );
  }

  confirmInlineSuccess(target: string, messageContains?: string) {
    cy.get(`${target} .v-messages__message`).should('be.visible');
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
    cy.get(`${target} .v-messages__message`).should('not.exist');
  }

  confirmInlineFailure(target: string, messageContains?: string) {
    cy.get(`${target} .v-messages__message`).should('be.visible');
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
    cy.get(`${target} .v-messages__message`).should('not.exist');
  }
}
