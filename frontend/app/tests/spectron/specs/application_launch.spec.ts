import { Application } from 'spectron';
import * as spectron from 'spectron';
import { testWithSpectron } from 'vue-cli-plugin-electron-builder/index';
import { captureOnFailure, GLOBAL_TIMEOUT } from './utils/common';

jest.setTimeout(GLOBAL_TIMEOUT);

describe('application launch', () => {
  let app: Application;
  let stopServe: () => Promise<Application>;

  beforeEach(async () => {
    ({ app, stopServe } = await testWithSpectron(spectron));
  });

  afterEach(async () => {
    await captureOnFailure(app);
    await stopServe();
  });

  it('make sure we get the login popup', async () => {
    const element = await app.client.$('.login');
    await expect(element.waitForExist({ timeout: 5000 })).resolves.toEqual(
      true
    );
  });
});
