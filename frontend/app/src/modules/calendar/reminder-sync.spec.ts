import { describe, expect, it } from 'vitest';
import { planReminderSync, type StoredReminder } from '@/modules/calendar/reminder-sync';

describe('planReminderSync', () => {
  const stored: StoredReminder[] = [
    { identifier: 1, secsBefore: 900 },
    { identifier: 2, secsBefore: 3600 },
  ];

  it('should plan nothing when the rows match what is stored', () => {
    const plan = planReminderSync(stored, [
      { identifier: 1, secsBefore: 900 },
      { identifier: 2, secsBefore: 3600 },
    ]);

    expect(plan).toEqual({ added: [], deleted: [], updated: [] });
  });

  it('should create a reminder for a row that has no identifier', () => {
    const plan = planReminderSync(stored, [
      { identifier: 1, secsBefore: 900 },
      { identifier: 2, secsBefore: 3600 },
      { secsBefore: 7200 },
    ]);

    expect(plan.added).toEqual([7200]);
    expect(plan.deleted).toEqual([]);
    expect(plan.updated).toEqual([]);
  });

  it('should create every reminder when the event has none yet', () => {
    const plan = planReminderSync([], [{ secsBefore: 900 }, { secsBefore: 7200 }]);

    expect(plan.added).toEqual([900, 7200]);
    expect(plan.deleted).toEqual([]);
  });

  it('should update a row whose interval changed', () => {
    const plan = planReminderSync(stored, [
      { identifier: 1, secsBefore: 1800 },
      { identifier: 2, secsBefore: 3600 },
    ]);

    expect(plan.updated).toEqual([{ identifier: 1, secsBefore: 1800 }]);
    expect(plan.added).toEqual([]);
    expect(plan.deleted).toEqual([]);
  });

  it('should delete a stored reminder whose row is gone', () => {
    const plan = planReminderSync(stored, [{ identifier: 1, secsBefore: 900 }]);

    expect(plan.deleted).toEqual([2]);
    expect(plan.added).toEqual([]);
    expect(plan.updated).toEqual([]);
  });

  it('should delete every reminder when all the rows are gone', () => {
    const plan = planReminderSync(stored, []);

    expect(plan.deleted).toEqual([1, 2]);
  });

  it('should not add a row that duplicates the interval of a kept row', () => {
    const plan = planReminderSync(stored, [
      { identifier: 1, secsBefore: 900 },
      { identifier: 2, secsBefore: 3600 },
      { secsBefore: 900 },
    ]);

    expect(plan.added).toEqual([]);
  });

  it('should add only one of two new rows sharing an interval', () => {
    const plan = planReminderSync([], [{ secsBefore: 900 }, { secsBefore: 900 }]);

    expect(plan.added).toEqual([900]);
  });

  it('should add an interval freed by an update in the same plan, not drop it as a duplicate', () => {
    const plan = planReminderSync(stored, [
      { identifier: 1, secsBefore: 1800 },
      { identifier: 2, secsBefore: 3600 },
      { secsBefore: 900 },
    ]);

    expect(plan.updated).toEqual([{ identifier: 1, secsBefore: 1800 }]);
    expect(plan.added).toEqual([900]);
  });

  it('should treat a row whose reminder was deleted elsewhere as new', () => {
    const plan = planReminderSync(stored, [{ identifier: 99, secsBefore: 7200 }]);

    expect(plan.added).toEqual([7200]);
    expect(plan.deleted).toEqual([1, 2]);
    expect(plan.updated).toEqual([]);
  });

  it('should add and delete the zero-second reminder the in-time switch sets like any other', () => {
    expect(planReminderSync([], [{ secsBefore: 0 }]).added).toEqual([0]);
    expect(planReminderSync([{ identifier: 3, secsBefore: 0 }], []).deleted).toEqual([3]);
  });
});
