import { expect, type Request } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { confirmDialog } from '../../helpers/utils';
import { TagManagerPage } from '../../pages/tag-manager';

/**
 * A request the app sent, without the query: `GET /settings` for the core api,
 * `POST /colibri/user/logout` for colibri.
 */
function describeRequest(request: Request): string | undefined {
  const { pathname } = new URL(request.url());
  const path = /\/api\/1(\/.*)$/.exec(pathname)?.[1] ?? /(\/colibri\/.*)$/.exec(pathname)?.[1];
  return path ? `${request.method()} ${path}` : undefined;
}

/* A reload starts logged out and resumes the session the backend still holds. The resume must
   happen once and land on the page that was open: a second resume, started when the logged-in
   layout replaced the login one, used to replace the session and open the dashboard over it. */
test.describe.serial('session across a reload and a logout', () => {
  let ctx: SharedTestContext;
  let tagManager: TagManagerPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    tagManager = new TagManagerPage(ctx.sharedPage);
    await tagManager.visit();
    await tagManager.createTag('resume', 'kept across a reload');
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('resumes the session once, on the page that was open', async () => {
    const { sharedPage } = ctx;
    /** Each resume loads the account's settings once, so a second resume shows as a second read. */
    const settingsReads: string[] = [];
    const recordSettingsRead = (request: Request): void => {
      if (describeRequest(request) === 'GET /settings')
        settingsReads.push(request.url());
    };
    sharedPage.on('request', recordSettingsRead);

    await sharedPage.reload();
    await tagManager.expectTagVisible('resume');

    sharedPage.off('request', recordSettingsRead);
    await expect(sharedPage).toHaveURL(/#\/tag-manager/);
    expect(settingsReads).toHaveLength(1);
  });

  test('sends nothing for the session between the logout and the backend logout', async () => {
    const { sharedPage, username } = ctx;
    const backendLogout = `PATCH /users/${username}`;
    const sent: string[] = [];
    const record = (request: Request): void => {
      const described = describeRequest(request);
      if (described)
        sent.push(described);
    };

    await sharedPage.locator('[data-testid=user-menu-button]').click();
    await sharedPage.locator('[data-testid=logout-button]').click();
    sharedPage.on('request', record);
    await confirmDialog(sharedPage);
    await expect.poll(() => sent.includes(backendLogout)).toBe(true);
    sharedPage.off('request', record);

    expect(sent.slice(0, sent.indexOf(backendLogout) + 1)).toEqual(['POST /colibri/user/logout', backendLogout]);
  });
});
