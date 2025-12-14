import { type APIRequestContext, type BrowserContext, type Page, request, test } from '@playwright/test';
import { isCoverageEnabled, startCoverage, stopCoverage } from '../../coverage';
import { TEST_TIMEOUT_STANDARD, VIEWPORTS } from '../../helpers/constants';
import { generateUsername } from '../../helpers/utils';
import { RotkiApp } from '../../pages/rotki-app';

test.describe('accounts', () => {
  // Account creation tests can take longer due to actual backend account setup
  test.setTimeout(TEST_TIMEOUT_STANDARD);

  for (const viewport of VIEWPORTS) {
    test.describe.serial(`Viewport: ${viewport.name} (${viewport.width}x${viewport.height})`, () => {
      let username: string;
      let sharedContext: BrowserContext;
      let sharedPage: Page;
      let apiContext: APIRequestContext;
      let app: RotkiApp;

      test.beforeAll(async ({ browser }) => {
        username = generateUsername();

        // Create shared browser context and page with the specific viewport
        sharedContext = await browser.newContext({
          viewport: { width: viewport.width, height: viewport.height },
        });
        sharedPage = await sharedContext.newPage();

        // Start coverage collection if enabled
        if (isCoverageEnabled()) {
          await startCoverage(sharedPage);
        }

        // Create a manual request context for API calls
        apiContext = await request.newContext();

        // Initialize app once for all tests in this viewport group
        app = new RotkiApp(sharedPage, apiContext);
      });

      test.afterAll(async () => {
        // Stop coverage collection if enabled
        if (isCoverageEnabled() && sharedPage) {
          await stopCoverage(sharedPage);
        }
        await apiContext?.dispose();
        await sharedContext?.close();
      });

      test('create account', async () => {
        await app.createAccount(username);
        await app.logout();
      });

      test('login', async () => {
        // After logout we're already on the login page with animations disabled
        await app.login(username);
        await app.checkGetPremiumButton();
        await app.logout();
      });
    });
  }
});
