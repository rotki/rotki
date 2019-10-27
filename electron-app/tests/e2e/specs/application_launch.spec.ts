import { Application } from 'spectron';
import { captureOnFailure, GLOBAL_TIMEOUT, initSpectron } from './utils/common';

jest.setTimeout(GLOBAL_TIMEOUT);

describe('application launch', function() {
  let app: Application;
  let stop: () => Promise<Application>;

  beforeEach(async () => {
    const promise = await initSpectron();
    app = promise.application;
    stop = promise.stop;
  });

  afterEach(async function() {
    await captureOnFailure(app);
    await stop();
  });

  it('make sure we get the login popup', async () => {
    await expect(app.client.waitForExist('.login', 5000)).resolves.toEqual(
      true
    );
  });
});
