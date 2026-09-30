import { describe, expect, it } from 'vitest';
import { summarizeGroup } from './group-summary';
import { ActionUrgency } from './types';

function row(id: string, urgency: ActionUrgency, flags: { locked?: boolean; informational?: boolean } = {}): {
  id: string;
  urgency: ActionUrgency;
  locked: boolean;
  informational: boolean;
} {
  return { id, informational: flags.informational ?? false, locked: flags.locked ?? false, urgency };
}

describe('modules/core/action-center/group-summary', () => {
  it('should count every row the group holds', () => {
    expect(summarizeGroup([row('a', ActionUrgency.TODO), row('b', ActionUrgency.AUTOMATIC, { locked: true })], []).count).toBe(2);
  });

  it('should take the most pressing urgency among the rows', () => {
    const rows = [row('a', ActionUrgency.AUTOMATIC), row('b', ActionUrgency.DECISION), row('c', ActionUrgency.TODO)];

    expect(summarizeGroup(rows, []).urgency).toBe(ActionUrgency.DECISION);
  });

  it('should not let a set-aside or locked row set the urgency', () => {
    const rows = [
      row('snoozed', ActionUrgency.DECISION, { informational: true }),
      row('locked', ActionUrgency.DECISION, { locked: true }),
      row('todo', ActionUrgency.TODO),
    ];

    expect(summarizeGroup(rows, []).urgency).toBe(ActionUrgency.TODO);
  });

  it('should have no urgency when every row is set aside or locked', () => {
    const rows = [
      row('snoozed', ActionUrgency.DECISION, { informational: true }),
      row('locked', ActionUrgency.TODO, { locked: true }),
    ];

    expect(summarizeGroup(rows, []).urgency).toBeUndefined();
  });

  it('should say whether one of its rows is new', () => {
    const rows = [row('a', ActionUrgency.TODO), row('b', ActionUrgency.TODO)];

    expect(summarizeGroup(rows, ['b', 'elsewhere']).hasNew).toBe(true);
    expect(summarizeGroup(rows, ['elsewhere']).hasNew).toBe(false);
  });
});
