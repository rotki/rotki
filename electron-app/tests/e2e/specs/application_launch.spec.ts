import { Application } from 'spectron';
import { captureOnFailure, GLOBAL_TIMEOUT, initSpectron } from './utils/common';

jest.setTimeout(GLOBAL_TIMEOUT);

describe('application launch', () => {
  let application: Application;
  let stop: () => Promise<Application>;

  beforeEach(async () => {
    ({ application, stop } = await initSpectron());
  });

  afterEach(async () => {
    await captureOnFailure(application);
    await stop();
  });

  it('make sure we get the login popup', async () => {
    await expect(
      application.client.waitForExist('.login', 5000)
    ).resolves.toEqual(true);
  });
});
