import { expect, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from './constants';

/** How long one dismissal round waits on each step before the round is retried. */
const DISMISS_ROUND_TIMEOUT = 1000;

/** Opens the notification drawer from the bell in the app bar. */
export async function openNotificationDrawer(page: Page): Promise<void> {
  await page.getByTestId('notification-indicator-badge').getByRole('button').click();
  await page.getByTestId('close-notifications').waitFor({ state: 'visible' });
}

/** Closes the notification drawer. */
export async function closeNotificationDrawer(page: Page): Promise<void> {
  await page.getByTestId('close-notifications').click();
  await page.getByTestId('close-notifications').waitFor({ state: 'hidden' });
}

/**
 * Clears the notification popups and waits until none shows.
 *
 * @remarks
 * Popups stack over the top right corner of the page, so a leftover one intercepts a click meant
 * for whatever sits there. With several queued the popup offers "dismiss all"; a single one is
 * dismissed from its card. Every locator is scoped to the popup, since the drawer's cards share the
 * notification ids. A popup can also time out between the visibility check and the click, so each
 * round clicks with a short timeout and the whole sequence retries until no popup shows.
 */
export async function dismissNotificationPopups(page: Page): Promise<void> {
  const popup = page.getByTestId('notification-popup');
  const dismissAll = page.getByTestId('notification-popup-dismiss-all');

  await expect(async () => {
    if (await dismissAll.isVisible())
      await dismissAll.click({ timeout: DISMISS_ROUND_TIMEOUT });

    if (await popup.isVisible())
      await popup.locator('[data-id=notification_dismiss]').click({ timeout: DISMISS_ROUND_TIMEOUT });

    await expect(popup).toBeHidden({ timeout: DISMISS_ROUND_TIMEOUT });
  }).toPass({ timeout: TIMEOUT_MEDIUM });
}
