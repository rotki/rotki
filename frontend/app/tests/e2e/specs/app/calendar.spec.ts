import { expect, test } from '@playwright/test';
import dayjs from 'dayjs';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { CalendarPage } from '../../pages/calendar-page';

test.describe.serial('calendar', () => {
  let ctx: SharedTestContext;
  let page: CalendarPage;
  const today = dayjs();

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    page = new CalendarPage(ctx.sharedPage);
    await page.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('creates an event on the selected day', async () => {
    await page.createEvent({ name: 'team standup', description: 'morning sync' });
    await page.expectEventInSelected('team standup');
  });

  test('edits an event', async () => {
    await page.editEvent('team standup', {
      newName: 'team standup renamed',
      newDescription: 'updated description',
    });
    await page.expectEventInSelected('team standup renamed');
  });

  test('navigates to next and previous month', async () => {
    const startLabel = today.format('MMMM YYYY');
    const nextLabel = today.add(1, 'month').format('MMMM YYYY');

    await page.expectMonthLabel(startLabel);
    await page.goToNextMonth();
    await page.expectMonthLabel(nextLabel);
    await page.goToPrevMonth();
    await page.expectMonthLabel(startLabel);
  });

  test('deletes an event', async () => {
    await page.deleteEvent('team standup renamed');
    await page.expectNoEventInSelected('team standup renamed');
  });

  test('shows validation error when name is empty', async () => {
    await page.openAddDialog();
    await ctx.sharedPage.locator('[data-cy=bottom-dialog] [data-cy=confirm]').click();
    await expect(
      ctx.sharedPage.locator('[data-cy=bottom-dialog]').getByText('The name field cannot be empty'),
    ).toBeVisible();
    await page.cancelDialog();
  });

  test('cancel button closes the add dialog', async () => {
    await page.openAddDialog();
    await page.cancelDialog();
  });

  test('Today button returns to current month when on a different month', async () => {
    await page.expectTodayDisabled();
    await page.goToNextMonth();
    await page.expectMonthLabel(today.add(1, 'month').format('MMMM YYYY'));
    await page.expectTodayEnabled();
    await page.clickToday();
    await page.expectMonthLabel(today.format('MMMM YYYY'));
    await page.expectTodayDisabled();
  });
});
