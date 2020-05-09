export class AccountingSettingsPage {
  visit() {
    cy.get('.user-dropdown').click();
    cy.get('.user-dropdown__settings').click();
    cy.get('a.settings-accounting').click();
  }

  setTaxFreePeriodDays(value: string) {
    cy.get('.settings-accounting__taxfree-period-days input').clear();
    cy.get('.settings-accounting__taxfree-period-days input').type(value);
    cy.get('.settings-accounting__taxfree-period-days input').blur();
    this.confirmInlineSuccess(
      '.settings-accounting__taxfree-period-days',
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
      '.settings-accounting__asset-to-ignore div.v-select__selections input'
    ).click();
    cy.get(
      '.settings-accounting__asset-to-ignore div.v-select__selections input'
    ).type(`${asset}{enter}`);
    cy.get('.settings-accounting__buttons__add').click();
  }

  remIgnoredAsset(asset: string) {
    cy.get(
      '.settings-accounting__ignored-assets div.v-select__selections input'
    ).click();
    cy.get(
      '.settings-accounting__ignored-assets div.v-select__selections input'
    ).type(`${asset}{enter}`);
    cy.get('.settings-accounting__buttons__remove').click();
  }

  ignoredAssetCount(number: string) {
    cy.get('.settings-accounting__ignored-assets__badge').should(
      'include.text',
      number
    );
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
}
