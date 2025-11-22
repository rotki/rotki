import { AssetsManagerPage } from '../../pages/assets-manager-page';
import { RotkiApp } from '../../pages/rotki-app';
import { createUser } from '../../utils/user';

describe('assets', () => {
  let username: string;
  let app: RotkiApp;
  let page: AssetsManagerPage;

  before(() => {
    username = createUser();
    app = new RotkiApp();
    page = new AssetsManagerPage();
    app.fasterLogin(username);

    cy.intercept({
      method: 'GET',
      url: '/assets/ignored',
    }).as('getIgnoredAsset');

    cy.wait('@getIgnoredAsset', { timeout: 15000 }).its('response.statusCode').should('equal', 200);
  });

  describe('ignored asset settings', () => {
    let ignoredAssets = 0;
    before(() => {
      page.visit('asset-manager-managed');
      page.ignoredAssets().then((ignored) => {
        ignoredAssets = Number.parseInt(ignored);
      });
      page.selectShowAll();
    });

    it('add an ignored asset and validate UI message it has been added', () => {
      page.addIgnoredAsset('1SG');
    });

    it('add another 2 ignored assets and confirm count increased by 3', () => {
      page.addIgnoredAsset('ZIX');
      page.addIgnoredAsset('1CR');
      page.ignoredAssetCount(ignoredAssets + 3);
    });

    it('remove an ignored asset, and confirm count decreased by one', () => {
      page.removeIgnoredAsset('1SG');
      page.ignoredAssetCount(ignoredAssets + 2);
    });
  });

  describe('add asset', () => {
    before(() => {
      page.visit('asset-manager-managed');
    });

    it('should show modal with title, fields and button', () => {
      page.showAddAssetModal();
    });

    it('adds an EVM asset', () => {
      page.addAnEvmAsset();
    });

    it('adds a non EVM asset', () => {
      page.showAddAssetModal();
      page.addOtherAsset();
    });

    it('edit an asset', () => {
      page.editEvmAsset();
    });

    it('should delete the assets', () => {
      page.deleteAnEvmAsset();
      page.deleteOtherAsset();
    });
  });
});
