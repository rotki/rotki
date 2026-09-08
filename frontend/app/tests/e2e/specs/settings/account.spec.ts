import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { AccountSettingsPage } from '../../pages/account-settings-page';

test.describe.serial('settings::data & security', () => {
  let ctx: SharedTestContext;
  const password = '1234';
  const newPassword = '5678';

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('change user password', async () => {
    const pageUserSecurity = new AccountSettingsPage(ctx.sharedPage);
    await pageUserSecurity.visit();
    await pageUserSecurity.changePassword(password, newPassword);
    await pageUserSecurity.confirmSuccess();
  });

  test('verify the new password works, by logging out and back in with it', async () => {
    await ctx.app.relogin(ctx.username, newPassword);
  });
});
