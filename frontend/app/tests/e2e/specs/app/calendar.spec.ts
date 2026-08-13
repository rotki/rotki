import { expect } from '@playwright/test';
import dayjs from 'dayjs';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
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
    await ctx.sharedPage.locator('[data-testid=bottom-dialog] [data-testid=confirm]').click();
    await expect(
      ctx.sharedPage.locator('[data-testid=bottom-dialog]').getByText('The name field cannot be empty'),
    ).toBeVisible();
    await page.cancelDialog();
  });

  // The reminder rows validate as part of the event form. That used to happen implicitly, because
  // each row registered itself with the form's validator; it is now an explicit call, and this is
  // what proves the save is still gated on it.
  test('blocks saving while a reminder is out of range', async () => {
    await page.openAddDialog();
    await page.createEventFields({ name: 'quarterly review' });
    await page.addReminder('99999', 'Weeks');

    await page.submitDialog();

    await page.expectDialogOpen();
    await page.expectReminderError('Cannot set reminder more than 4 Weeks');
    await page.cancelDialog();
  });

  test('keeps a reminder attached to the event it was created with', async () => {
    await page.openAddDialog();
    await page.createEventFields({ name: 'release cut' });
    await page.addReminder('3', 'Days');
    await page.confirmDialog();

    await page.expectEventInSelected('release cut');

    // Reopening refetches the stored reminders, so this asserts what was persisted.
    await page.openEventByName('release cut');
    await page.expectReminderCount(1);
    await page.expectReminder('3', 'Days');
    await page.cancelDialog();

    await page.deleteEvent('release cut');
  });

  // The three below cover the persistence paths, which differ between creating and editing an
  // event: a new event's reminders are held back until it has an id, an existing one's are written
  // per row as they change.
  test('persists a reminder edited on an existing event', async () => {
    await page.createEvent({ name: 'sprint demo' });
    await page.openEventByName('sprint demo');
    await page.addReminder('2', 'Hours');
    await page.confirmDialog();

    await page.openEventByName('sprint demo');
    await page.changeReminderAmount('2', '5');
    await page.confirmDialog();

    await page.openEventByName('sprint demo');
    await page.expectReminder('5', 'Hours');
    await page.cancelDialog();
  });

  test('deletes a reminder that was already saved', async () => {
    await page.openEventByName('sprint demo');
    await page.expectReminderCount(1);
    await page.deleteReminder('5');
    await page.expectReminderCount(0);
    await page.confirmDialog();

    await page.openEventByName('sprint demo');
    await page.expectReminderCount(0);
    await page.cancelDialog();
  });

  test('adds a second reminder to an event that already has one', async () => {
    await page.openEventByName('sprint demo');
    await page.addReminder('1', 'Hours');
    await page.confirmDialog();

    await page.openEventByName('sprint demo');
    await page.addReminder('3', 'Hours');
    await page.confirmDialog();

    await page.openEventByName('sprint demo');
    await page.expectReminderAmounts(['1', '3']);
    await page.cancelDialog();

    await page.deleteEvent('sprint demo');
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
