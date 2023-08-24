import { RotkiApp } from './rotki-app';

export class AssetsManagerPage {
  visit(submenu: string) {
    RotkiApp.navigateTo('asset-manager', submenu);
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
    cy.get('[data-cy="table-filter"]').type(
      `{selectall}{backspace}symbol: ${asset}{enter}{esc}`
    );
    cy.get('.v-data-table__empty-wrapper').should('not.exist');
    cy.get('.v-data-table__progress').should('not.exist');
  }

  searchAssetByAddress(address: string) {
    cy.get('[data-cy="table-filter"]').type(
      `{selectall}{backspace}address: ${address}{enter}{esc}`
    );
    cy.get('.v-data-table__empty-wrapper').should('not.exist');
    cy.get('.v-data-table__progress').should('not.exist');
  }

  searchAssetBySymbol(symbol: string) {
    cy.get('[data-cy="table-filter"]').type(
      `{selectall}{backspace}symbol: ${symbol}{enter}{esc}`
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
    const waitForAssetDeleted = this.createWaitForDeleteManagedAssets();
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
    waitForAssetDeleted();
    cy.get('[data-cy=confirm-dialog]').should('not.be.exist');
  }

  deleteAnEvmAsset(address = '0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8') {
    this.searchAssetByAddress(address);
    cy.get('[data-cy=managed-assets-table] [data-cy=row-delete]').click();
    this.confirmDelete();
  }

  deleteOtherAsset(symbol = 'SYMBOL 2') {
    this.searchAssetBySymbol(symbol);
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
    cy.get('[data-cy=bottom-dialog] .v-card__title')
      .contains('Add a new asset')
      .should('be.visible');

    // on load the confirm button should be visible and enabled
    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').as('submitButton');
    cy.get('@submitButton').should('be.enabled');
    cy.get('@submitButton').click();
    // button should be enabled regardless of the validation status
    cy.get('@submitButton').should('be.enabled');
  }

  addAnEvmAsset(address = '0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8'): void {
    // get the fields
    cy.get('[data-cy=chain-select] [role=button]').as('chainInput');

    cy.get('[data-cy=token-select] [role=button]').as('tokenInput');

    cy.get('[data-cy=address-input] .v-text-field__slot input[type=text]').as(
      'addressInput'
    );

    cy.get('[data-cy=symbol-input] .v-text-field__slot input[type=text]').as(
      'symbolInput'
    );

    cy.get('[data-cy=decimal-input] .v-text-field__slot input[type=number]').as(
      'decimalInput'
    );

    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').as('submitButton');

    // Frontend validation for address
    cy.get('@submitButton').click();

    cy.get('[data-cy=address-input] .v-messages__message').as('addressMessage');
    cy.get('@addressMessage')
      .contains('The value is required')
      .should('be.visible');

    // enter address
    cy.get('@addressInput').type(address);
    cy.get('@submitButton').click();

    cy.get('[data-cy=chain-select] .v-messages__message').as('chainMessage');
    cy.get('[data-cy=token-select] .v-messages__message').as('tokenMessage');
    cy.get('[data-cy=decimal-input] .v-messages__message').as('decimalMessage');

    // expect to see backend validation messages
    cy.get('@chainMessage').scrollIntoView();
    cy.get('@chainMessage')
      .contains('Field may not be null.')
      .should('be.visible');
    cy.get('@tokenMessage')
      .contains('Field may not be null.')
      .should('be.visible');
    cy.get('@decimalMessage')
      .contains('Field may not be null.')
      .should('be.visible');

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

    // after loading, input should be enabled
    cy.get('@addressInput').should('be.enabled');

    const symbol = 'SYMBOL 1';
    // enter symbol
    cy.get('@symbolInput').clear();
    cy.get('@symbolInput').type(symbol);

    // enter decimals
    cy.get('@decimalInput').clear();
    cy.get('@decimalInput').type('2');

    // at this point, no validation message, button should be enabled
    cy.get('@submitButton').should('be.enabled');
    // create the asset
    cy.get('@submitButton').click();
    // dialog should not be visible
    cy.get('[data-cy=bottom-dialog]').should('not.be.visible');

    // search the asset
    this.searchAssetByAddress(address);

    cy.get('[data-cy=managed-assets-table] [data-cy="details-symbol"]').should(
      'contain',
      symbol
    );
  }

  addOtherAsset() {
    // get the fields
    cy.get('[data-cy=type-select] [role=button]').as('typeInput');
    cy.get('[data-cy=name-input] .v-text-field__slot input[type=text]').as(
      'nameInput'
    );
    cy.get('[data-cy=symbol-input] .v-text-field__slot input[type=text]').as(
      'symbolInput'
    );

    cy.get('@typeInput').click();
    cy.get('.v-menu__content.menuable__content__active .v-list-item')
      .contains('Own chain')
      .click();

    cy.get('@nameInput').clear();
    cy.get('@nameInput').type('NAME 2');

    const symbol = 'SYMBOL 2';
    cy.get('@symbolInput').clear();
    cy.get('@symbolInput').type('SYMBOL 2');

    // at this point, no validation message, button should be enabled
    cy.get('@submitButton').should('be.enabled');
    // create the asset
    cy.get('@submitButton').click();
    // dialog should not be visible
    cy.get('[data-cy=bottom-dialog]').should('not.be.visible');

    // search the asset
    this.searchAssetBySymbol(symbol);

    cy.get('[data-cy=managed-assets-table] [data-cy="details-symbol"]').should(
      'contain',
      symbol
    );
  }

  editEvmAsset(address = '0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8'): void {
    // search the asset
    this.searchAssetByAddress(address);

    // click edit button
    cy.get('[data-cy=managed-assets-table] [data-cy=row-edit]').click();

    // dialog should be visible
    cy.get('[data-cy=bottom-dialog]').should('be.visible');
    // dialog title should match as well
    cy.get('[data-cy=bottom-dialog] .v-card__title')
      .contains('Edit an asset')
      .should('be.visible');

    cy.get('[data-cy=symbol-input] .v-text-field__slot input[type=text]').as(
      'symbolInput'
    );

    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').as('submitButton');

    const symbol = 'SYMBOL 3';
    // edit symbol
    cy.get('@symbolInput').clear();
    cy.get('@symbolInput').type(symbol);

    // at this point, no validation message, button should be enabled
    cy.get('@submitButton').should('be.enabled');
    // create the asset
    cy.get('@submitButton').click();

    // dialog should not be visible
    cy.get('[data-cy=bottom-dialog]').should('not.be.visible');

    cy.get('[data-cy=managed-assets-table] [data-cy="details-symbol"]').should(
      'contain',
      symbol
    );
  }
}
