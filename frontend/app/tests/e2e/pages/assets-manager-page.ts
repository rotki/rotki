import { RotkiApp } from './rotki-app';

export class AssetsManagerPage {
  visit(submenu: string) {
    RotkiApp.navigateTo('asset-manager', submenu);
  }

  openStatusFilter() {
    cy.get('[data-cy=status-filter]').scrollIntoView();
    cy.get('[data-cy=status-filter]').should('be.visible');
    cy.get('[data-cy=status-filter]').click();
    cy.get('[data-cy=asset-filter-menu]').should('exist');
  }

  closeStatusFilter() {
    cy.get('[data-cy=status-filter]').click();
    cy.get('[data-cy=asset-filter-menu]').should('not.exist');
  }

  ignoredAssets() {
    this.openStatusFilter();
    return cy
      .get('[data-cy=asset-filter-show_only]')
      .invoke('text')
      .then((text) => {
        this.closeStatusFilter();
        cy.wrap(text.replace(/[^\d.]/g, ''));
      });
  }

  ignoredAssetCount(number: number) {
    this.openStatusFilter();
    cy.get('[data-cy=asset-filter-show_only]').should('include.text', number.toString());
    this.closeStatusFilter();
  }

  visibleEntries(visible: number) {
    // the total row is added to the visible entries
    cy.get('[data-cy=managed-assets-table] tbody').find('tr').should('have.length', visible);
  }

  focusOnTableFilter() {
    cy.get('[data-cy=table-filter] [data-id=activator]').then(($activator) => {
      const arrowButton = $activator.find('> span:last-child');
      cy.wrap(arrowButton).click();
      const clearButton = $activator.find('> button:nth-child(3)');
      if (clearButton && clearButton.length > 0) {
        cy.wrap(clearButton).click();
        cy.wrap(arrowButton).click();
      }
    });
  }

  searchAsset(asset: string) {
    this.focusOnTableFilter();
    cy.get('[data-cy=table-filter] input').type(`symbol: ${asset}`);
    cy.get('[data-cy=table-filter] input').type(`{enter}{esc}`);
    cy.get('div[class*=thead__loader]').should('not.exist');
    this.visibleEntries(1);
  }

  searchAssetByAddress(address: string) {
    this.focusOnTableFilter();
    cy.get('[data-cy=table-filter] input').type(`address: ${address}`);
    cy.get('[data-cy=table-filter] input').type(`{enter}{esc}`);
    cy.get('div[class*=thead__loader]').should('not.exist');
    this.visibleEntries(1);
  }

  addIgnoredAsset(asset: string) {
    this.searchAsset(asset);

    cy.get('[data-cy=managed-assets-table] > div > table > tbody > tr:first-child td:nth-child(6) input').then(
      ($switch) => {
        const initialValue = $switch.is(':checked');
        expect(initialValue, 'false');
        cy.get('[data-cy=managed-assets-table] > div > table > tbody > tr:first-child td:nth-child(6) input').click();
        cy.get('[data-cy=managed-assets-table] > div > table > tbody > tr:first-child td:nth-child(6) input').should(
          'be.checked',
        );
      },
    );
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
  }

  selectShowAll(): void {
    this.openStatusFilter();
    cy.get('[data-cy=asset-filter-none]').scrollIntoView();
    cy.get('[data-cy=asset-filter-none]').click();
    this.closeStatusFilter();
  }

  removeIgnoredAsset(asset: string) {
    this.searchAsset(asset);
    cy.get('[data-cy=managed-assets-table] > div > table > tbody > tr:first-child td:nth-child(6) input').then(
      ($switch) => {
        const initialValue = $switch.is(':checked');
        expect(initialValue, 'true');
        cy.get('[data-cy=managed-assets-table] > div > table > tbody > tr:first-child td:nth-child(6) input').click();
        cy.get('[data-cy=managed-assets-table] > div > table > tbody > tr:first-child td:nth-child(6) input').should(
          'not.be.checked',
          'false',
        );
      },
    );
  }

  createWaitForDeleteManagedAssets() {
    cy.intercept({
      method: 'DELETE',
      url: '/api/1/assets/all**',
    }).as('apiCall');

    return () => {
      // Wait for response.status to be 200
      cy.wait('@apiCall', { timeout: 30000 }).its('response.statusCode').should('equal', 200);
    };
  }

  confirmDelete() {
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=dialog-title]').should('contain', 'Delete asset');
    const waitForAssetDeleted = this.createWaitForDeleteManagedAssets();
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
    waitForAssetDeleted();
    cy.get('[data-cy=confirm-dialog]').should('not.exist');
  }

  deleteAnEvmAsset(address = '0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8') {
    this.searchAssetByAddress(address);
    cy.get('[data-cy=managed-assets-table] [data-cy=row-delete]').click();
    this.confirmDelete();
  }

  deleteOtherAsset(symbol = 'SYMBOL 2') {
    this.searchAsset(symbol);
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
    cy.get('[data-cy=bottom-dialog] h5').contains('Add a new asset').should('be.visible');

    // on load the confirm button should be visible and enabled
    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').as('submitButton');
    cy.get('@submitButton').should('be.enabled');
    cy.get('@submitButton').click();
    // button should be enabled regardless of the validation status
    cy.get('@submitButton').should('be.enabled');
  }

  addAnEvmAsset(address = '0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8'): void {
    // get the fields
    cy.get('[data-cy=chain-select]').as('chainInput');

    cy.get('[data-cy=token-select]').as('tokenInput');

    cy.get('[data-cy=address-input] input').as('addressInput');

    cy.get('[data-cy=name-input] input').as('nameInput');

    cy.get('[data-cy=symbol-input] input').as('symbolInput');

    cy.get('[data-cy=decimal-input] input[type=number]').as('decimalInput');

    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').as('submitButton');

    // Frontend validation for address
    cy.get('@submitButton').trigger('click');

    cy.get('[data-cy=address-input] .details').as('addressMessage');
    cy.get('@addressMessage').contains('The value is required').should('be.visible');

    // enter address
    cy.get('@addressInput').type(address);
    cy.get('@submitButton').click();

    cy.get('[data-cy=chain-select] .details').as('chainMessage');
    cy.get('[data-cy=token-select] .details').as('tokenMessage');
    cy.get('[data-cy=decimal-input] .details').as('decimalMessage');

    // expect to see backend validation messages
    cy.get('@chainMessage').scrollIntoView();
    cy.get('@chainMessage').contains('Field may not be null.').should('be.visible');
    cy.get('@tokenMessage').contains('Field may not be null.').should('be.visible');
    cy.get('@decimalMessage').contains('Field may not be null.').should('be.visible');

    cy.get('@chainMessage').should('not.be.empty');
    // select a chain
    cy.get('@chainInput').click();
    cy.get('[role="menu-content"] button[type="button"]').first().click();
    // selecting a chain should clear the validation message
    cy.get('@chainMessage').should('be.empty');

    cy.get('@tokenMessage').should('not.be.empty');
    // select a token
    cy.get('@tokenInput').click();
    cy.get('[role="menu-content"] button[type="button"]').first().click();
    // selecting a chain should clear the validation message
    cy.get('@tokenMessage').should('be.empty');

    // after loading, input should be enabled
    cy.get('@addressInput').should('be.enabled');

    // enter name
    cy.get('@nameInput').clear();
    cy.get('@nameInput').type('ASSET NAME 1');

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
    cy.get('[data-cy=bottom-dialog]').should('not.exist');

    // search the asset
    this.searchAssetByAddress(address);

    cy.get('[data-cy=managed-assets-table] [data-cy=list-title]').should('contain', symbol);
  }

  addOtherAsset() {
    // get the fields
    cy.get('[data-cy=type-select]').as('typeInput');
    cy.get('[data-cy=name-input] input').as('nameInput');
    cy.get('[data-cy=symbol-input] input').as('symbolInput');

    cy.get('@typeInput').click();
    cy.get('[role="menu-content"] button[type="button"]').contains('Own chain').click();

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
    cy.get('[data-cy=bottom-dialog]').should('not.exist');

    // search the asset
    this.searchAsset(symbol);

    cy.get('[data-cy=managed-assets-table] [data-cy=list-title]').should('contain', symbol);
  }

  editEvmAsset(address = '0xfDb7EEc5eBF4c4aC7734748474123aC25C6eDCc8'): void {
    // search the asset
    this.searchAssetByAddress(address);

    // click edit button
    cy.get('[data-cy=managed-assets-table] [data-cy=row-edit]').click();

    // dialog should be visible
    cy.get('[data-cy=bottom-dialog]').should('be.visible');
    // dialog title should match as well
    cy.get('[data-cy=bottom-dialog] h5').contains('Edit an asset').should('be.visible');

    cy.get('[data-cy=symbol-input] input').as('symbolInput');

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
    cy.get('[data-cy=bottom-dialog]').should('not.exist');

    cy.get('[data-cy=managed-assets-table] [data-cy=list-title]').should('contain', symbol);
  }
}
