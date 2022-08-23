import { Guid } from '../../common/guid';
import { AssetsManagerPage } from '../pages/assets-manager-page';
import { RotkiApp } from '../pages/rotki-app';

describe('assets', () => {
  let username: string;
  let app: RotkiApp;
  let page: AssetsManagerPage;

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new AssetsManagerPage();
    app.fasterLogin(username);
  });

  describe('ignored asset settings', () => {
    let ignoredAssets = 0;
    before(() => {
      page.visit();
      page.ignoredAssets().then(ignored => {
        ignoredAssets = parseInt(ignored);
      });
    });

    it('add an ignored asset and validate UI message it has been added', () => {
      page.addIgnoredAsset('1SG');
    });

    it('add another 2 ignored assets and confirm count increased by 3', () => {
      page.addIgnoredAsset('ZIX');
      page.addIgnoredAsset('1CR');
      // @ts-ignore
      page.ignoredAssetCount(ignoredAssets + 3);
    });

    it('remove an ignored asset, and confirm count decreased by one', () => {
      page.removeIgnoredAsset('1SG');
      // @ts-ignore
      page.ignoredAssetCount(ignoredAssets + 2);
    });
  });
});
