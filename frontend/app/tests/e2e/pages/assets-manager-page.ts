export class AssetsManagerPage {
  visit() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__asset-manager').scrollIntoView();
    cy.get('.navigation__asset-manager').click();
    cy.get('[data-cy="managed-assets-table"]').should('be.visible');
  }

  ignoredAssets() {
    cy.get('[data-cy=asset-filter]').click();
    return cy
      .get('[data-cy=asset-filter-ignored] .v-radio:nth-child(3)')
      .invoke('text')
      .then(text => {
        cy.get('[data-cy=asset-filter]').click();
        cy.wrap(text.replace(/[^\d.]/g, ''));
      });
  }

  ignoredAssetCount(number: number) {
    cy.get('[data-cy=asset-filter]').click();
    cy.get('[data-cy=asset-filter-menu]').should('be.visible');
    cy.get('[data-cy=asset-filter-ignored] .v-radio:nth-child(3)').should(
      'include.text',
      number.toString()
    );
    cy.get('[data-cy=asset-filter]').click();
    cy.get('[data-cy=asset-filter-menu]').should('not.be.visible');
  }

  searchAsset(asset: string) {
    cy.get('[data-cy=asset_table_filter]').type(
      `{selectall}{backspace}symbol: ${asset}{enter}{esc}`
    );
    cy.get('.v-data-table__empty-wrapper').should('not.exist');
    cy.get('.v-data-table__progress').should('not.exist');
  }

  searchAsseAddress(address: string) {
    cy.get('[data-cy=asset_table_filter]').type(
      `{selectall}{backspace}address: ${address}{enter}{esc}`
    );
    cy.get('.v-data-table__empty-wrapper').should('not.exist');
    cy.get('.v-data-table__progress').should('not.exist');
  }

  addIgnoredAsset(asset: string) {
    this.searchAsset(asset);

    cy.get(
      '.v-data-table__wrapper tbody tr:first-child td:nth-child(6) input'
    ).then($switch => {
      const initialValue = $switch.attr('aria-checked');
      expect(initialValue, 'false');
      cy.get(
        '.v-data-table__wrapper tbody tr:first-child td:nth-child(6)'
      ).click();
      cy.get(
        '.v-data-table__wrapper tbody tr:first-child td:nth-child(6)'
      ).then(() => {
        expect($switch.attr('aria-checked')).not.to.eq(initialValue);
      });
    });
  }

  selectShowAll(): void {
    cy.get('[data-cy=asset-filter]').scrollIntoView();
    cy.get('[data-cy=asset-filter]').click();
    cy.get('[data-cy=asset-filter-menu]').should('be.visible');
    cy.get(
      '[data-cy=asset-filter-ignored] .v-radio:first-child'
    ).scrollIntoView();
    cy.get('[data-cy=asset-filter-ignored] .v-radio:first-child').click();
    cy.get('[data-cy=asset-filter]').click();
    cy.get('[data-cy=asset-filter-menu]').should('not.be.visible');
  }

  removeIgnoredAsset(asset: string) {
    this.searchAsset(asset);
    cy.get(
      '.v-data-table__wrapper tbody tr:first-child td:nth-child(6) input'
    ).then($switch => {
      const initialValue = $switch.attr('aria-checked');
      expect(initialValue, 'true');
      cy.get(
        '.v-data-table__wrapper tbody tr:first-child td:nth-child(6)'
      ).click();
      cy.get(
        '.v-data-table__wrapper tbody tr:first-child td:nth-child(6)'
      ).then(() => {
        expect($switch.attr('aria-checked')).not.to.eq(initialValue);
      });
    });
  }

  createWaitForDeleteManagedAssets() {
    cy.intercept({
      method: 'DELETE',
      url: '/api/1/assets/all**'
    }).as('apiCall');

    return () => {
      // Wait for response.status to be 200
      cy.wait('@apiCall', { timeout: 30000 })
        .its('response.statusCode')
        .should('equal', 200);
    };
  }

  confirmDelete() {
    cy.get('[data-cy=confirm-dialog]')
      .find('[data-cy=dialog-title]')
      .should('contain', 'Delete asset');
    const waitForLedgerActions = this.createWaitForDeleteManagedAssets();
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
    waitForLedgerActions();
    cy.get('[data-cy=confirm-dialog]').should('not.be.exist');
  }

  deleteAsset(address: string) {
    this.searchAsseAddress(address);
    cy.get('[data-cy=managed-assets-table] [data-cy=row-delete]').click();
    this.confirmDelete();
  }

  showAddAssetModal(): void {
    cy.get('[data-cy=managed-asset-add-btn]').scrollIntoView();
    // click the add asset button
    cy.get('[data-cy=managed-asset-add-btn]').click();
    // dialog should be visible
    cy.get('[data-cy=bottom-dialog]').should('be.visible');
    // dialog title should match as well
    cy.get('[data-cy=bottom-dialog] .card-title')
      .contains('Add a new asset')
      .should('be.visible');

    // on load the confirm button should be visible and enabled
    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').as('submitButton');
    cy.get('@submitButton').should('be.enabled');
    cy.get('@submitButton').click();
    // on empty form click, backend validation should make the button disabled
    cy.get('@submitButton').should('be.disabled');

    // expect to see backend validation messages
    cy.get('[data-cy=chain-select] .v-messages__message')
      .contains('Field may not be null.')
      .should('be.visible');
    cy.get('[data-cy=token-select] .v-messages__message')
      .contains('Field may not be null.')
      .should('be.visible');
    cy.get('[data-cy=address-input] .v-messages__message')
      .contains('Given value is not an ethereum address')
      .should('be.visible');
    cy.get('[data-cy=decimal-input] .v-messages__message')
      .contains('Field may not be null.')
      .should('be.visible');
  }

  addAsset(): void {
    const ethAddress = '0x9737c028a738f0856c86bc6279b356db8f3dd440';
    // get the fields
    cy.get('[data-cy=chain-select] [role=button]').as('chainInput');
    cy.get('[data-cy=chain-select] .v-messages__message')
      .contains('Field may not be null.')
      .as('chainMessage');

    cy.get('[data-cy=token-select] [role=button]').as('tokenInput');
    cy.get('[data-cy=token-select] .v-messages__message')
      .contains('Field may not be null.')
      .as('tokenMessage');

    cy.get('[data-cy=address-input] .v-text-field__slot input[type=text]').as(
      'addressInput'
    );
    cy.get('[data-cy=address-input] .v-messages__message')
      .contains('Given value is not an ethereum address')
      .as('addressMessage');

    cy.get('[data-cy=decimal-input] .v-text-field__slot input[type=number]').as(
      'decimalInput'
    );
    cy.get('[data-cy=decimal-input] .v-messages__message')
      .contains('Field may not be null.')
      .as('decimalMessage');

    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').as('submitButton');

    cy.get('@chainMessage').should('be.visible');
    // select a chain
    cy.get('@chainInput').click();
    cy.get('.v-menu__content.menuable__content__active .v-list-item__title')
      .first()
      .click();
    // selecting a chain should clear the validation message
    cy.get('@chainMessage').should('not.be.visible');

    cy.get('@tokenMessage').should('be.visible');
    // select a token
    cy.get('@tokenInput').click();
    cy.get('.v-menu__content.menuable__content__active .v-list-item__title')
      .first()
      .click();
    // selecting a chain should clear the validation message
    cy.get('@tokenMessage').should('not.be.visible');

    cy.get('@addressMessage').should('be.visible');
    // enter address
    cy.get('@addressInput').type(ethAddress);
    cy.get('@decimalMessage').should('be.visible');
    // after loading, input should be enabled
    cy.get('@addressInput').should('be.enabled');

    // enter decimals
    cy.get('@decimalInput').clear();
    cy.get('@decimalInput').type('2');

    // at this point, no validation message, button should be enabled
    cy.get('@submitButton').should('be.enabled');
    // create the asset
    cy.get('@submitButton').click();
    // button should be visible at loading state
    cy.get('@submitButton').should('be.disabled');

    // dialog should not be visible
    cy.get('[data-cy=bottom-dialog]').should('not.be.visible');
    this.deleteAsset(ethAddress);
  }
}
