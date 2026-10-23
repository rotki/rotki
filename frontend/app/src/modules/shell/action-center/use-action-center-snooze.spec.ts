import type { EffectScope } from 'vue';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';
import { type ActionItem, type ActionItemOption, type ActionTarget, ActionUrgency, createActionItem } from '@/modules/core/action-center/types';
import { HISTORY_SYNC_ROW_ID } from '@/modules/shell/action-center/row-ids';
import { SetAside, type SetAsideChange, useActionCenterSnooze } from '@/modules/shell/action-center/use-action-center-snooze';

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

function row(id: string, overrides: Partial<ActionItem> = {}): ActionItem {
  return {
    ...createActionItem<ActionTarget, string>({
      actionLabel: 'act',
      count: 3,
      description: 'description',
      icon: 'lu-key-round',
      id,
      target: { kind: 'route', to: { name: '/accounts/' } },
      title: id,
      urgency: ActionUrgency.DECISION,
    }),
    ...overrides,
  };
}

function optionIds(item: ActionItem): string[] {
  return item.options.map(option => option.id);
}

function run(item: ActionItem, id: string): void {
  const option: ActionItemOption | undefined = item.options.find(candidate => candidate.id === id);
  assert(option?.target.kind === 'run');
  option.target.run();
}

let scope: EffectScope | undefined;

function snooze(): ReturnType<typeof useActionCenterSnooze> {
  scope = effectScope();
  const result = scope.run(() => useActionCenterSnooze());
  assert(result);
  return result;
}

describe('modules/shell/action-center/use-action-center-snooze', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: new Date('2026-09-23T10:00:00Z') });
    localStorage.clear();
    set(useLoggedUserIdentifier(), 'alice');
  });

  afterEach(() => {
    scope?.stop();
    vi.useRealTimers();
  });

  it.each([
    ['a decision', ActionUrgency.DECISION],
    ['work that resolves once data is processed', ActionUrgency.TODO],
    ['what rotki retries on its own, which still counts toward the badge', ActionUrgency.AUTOMATIC],
  ])('should offer a snooze and a mute on %s', (_name, urgency) => {
    const { withSnooze } = snooze();

    expect(optionIds(withSnooze(row(urgency, { urgency })))).toEqual(['remind-later', 'mute']);
  });

  it.each([
    ['a locked row', row('locked', { locked: true })],
    ['a row already set aside', row('set-aside', { informational: true })],
    ['the history sync row, which has a dismissal of its own', row(HISTORY_SYNC_ROW_ID, { urgency: ActionUrgency.TODO })],
  ])('should offer no snooze on %s', (_name, item) => {
    const { withSnooze } = snooze();

    expect(optionIds(withSnooze(item))).not.toContain('remind-later');
  });

  it('should list the snooze ahead of the option that silences a row for good', () => {
    const { withSnooze } = snooze();
    const suppress: ActionItemOption = { danger: true, icon: 'lu-bell-off', id: 'do-not-show-again', label: 'x', target: { kind: 'run', run: vi.fn() } };
    const guide: ActionItemOption = { icon: 'lu-book-open', id: 'guide', label: 'y', target: { kind: 'external', url: 'https://docs.rotki.com' } };

    expect(optionIds(withSnooze(row('key', { options: [suppress, guide] })))).toEqual(['guide', 'remind-later', 'do-not-show-again']);
  });

  it('should set a snoozed row aside, offering to bring it back, and report the change', () => {
    const { onSnoozeChange, withSnooze } = snooze();
    const changed = vi.fn<(change: SetAsideChange) => void>();
    onSnoozeChange(changed);

    run(withSnooze(row('key')), 'remind-later');
    const snoozed = withSnooze(row('key'));

    expect(snoozed.informational).toBe(true);
    expect(snoozed.status).toMatch(/^action_center\.set_aside\.snoozed_until::\D*30\D*$/);
    expect(optionIds(snoozed)).toEqual(['remind-now', 'mute']);
    expect(changed).toHaveBeenCalledWith({ from: undefined, id: 'key' });
  });

  it('should leave a row that is not set aside without a status', () => {
    const { withSnooze } = snooze();

    expect(withSnooze(row('key')).status).toBeUndefined();
  });

  it('should offer a mute after the snooze on a row that has no way to silence it for good', () => {
    const { withSnooze } = snooze();

    expect(optionIds(withSnooze(row('key')))).toEqual(['remind-later', 'mute']);
  });

  it('should offer no mute on a row that already has a way to silence it for good', () => {
    const { withSnooze } = snooze();
    const suppress: ActionItemOption = { danger: true, icon: 'lu-bell-off', id: 'do-not-show-again', label: 'x', target: { kind: 'run', run: vi.fn() } };

    expect(optionIds(withSnooze(row('key', { options: [suppress] })))).not.toContain('mute');
  });

  it.each([
    ['a locked row', row('locked', { locked: true })],
    ['the history sync row', row(HISTORY_SYNC_ROW_ID, { urgency: ActionUrgency.TODO })],
  ])('should offer no mute on %s', (_name, item) => {
    const { withSnooze } = snooze();

    expect(optionIds(withSnooze(item))).not.toContain('mute');
  });

  it('should report which rows were snoozed and which were muted', () => {
    const { setAsideOf, withSnooze } = snooze();
    run(withSnooze(row('snoozed')), 'remind-later');
    run(withSnooze(row('muted')), 'mute');

    expect(setAsideOf(row('snoozed'))).toBe(SetAside.SNOOZED);
    expect(setAsideOf(row('muted'))).toBe(SetAside.MUTED);
    expect(setAsideOf(row('other'))).toBeUndefined();
  });

  it('should set a muted row aside, offering only to unmute it, and report the change', () => {
    const { onSnoozeChange, withSnooze } = snooze();
    const changed = vi.fn<(change: SetAsideChange) => void>();
    onSnoozeChange(changed);

    run(withSnooze(row('key')), 'mute');
    const muted = withSnooze(row('key'));

    expect(muted.informational).toBe(true);
    expect(muted.status).toBe('action_center.set_aside.muted');
    expect(optionIds(muted)).toEqual(['unmute']);
    expect(changed).toHaveBeenCalledWith({ from: undefined, id: 'key' });
  });

  it('should keep a muted row set aside however much its count grows, and for good', async () => {
    const { withSnooze } = snooze();
    run(withSnooze(row('key', { count: 3 })), 'mute');

    await vi.advanceTimersByTimeAsync(WEEK_MS * 4);

    expect(withSnooze(row('key', { count: 30 })).informational).toBe(true);
  });

  it('should turn a snooze into a mute, so the row stays away past the week', async () => {
    const { setAsideOf, withSnooze } = snooze();
    run(withSnooze(row('key')), 'remind-later');
    run(withSnooze(row('key')), 'mute');

    await vi.advanceTimersByTimeAsync(WEEK_MS);

    expect(setAsideOf(row('key'))).toBe(SetAside.MUTED);
  });

  it('should bring a muted row back when unmuted, and report the change', () => {
    const { onSnoozeChange, withSnooze } = snooze();
    const changed = vi.fn<(change: SetAsideChange) => void>();
    run(withSnooze(row('key')), 'mute');
    onSnoozeChange(changed);

    run(withSnooze(row('key')), 'unmute');

    expect(withSnooze(row('key')).informational).toBe(false);
    expect(optionIds(withSnooze(row('key')))).toEqual(['remind-later', 'mute']);
    expect(changed).toHaveBeenCalledWith({ from: SetAside.MUTED, id: 'key' });
  });

  it('should keep each user\'s mutes apart', async () => {
    const { withSnooze } = snooze();
    run(withSnooze(row('key')), 'mute');
    await nextTick();

    set(useLoggedUserIdentifier(), 'bob');
    await nextTick();

    expect(withSnooze(row('key')).informational).toBe(false);
  });

  it('should count the row again once its count grows past what it was when snoozed', () => {
    const { withSnooze } = snooze();
    run(withSnooze(row('key', { count: 3 })), 'remind-later');

    expect(withSnooze(row('key', { count: 2 })).informational).toBe(true);
    expect(withSnooze(row('key', { count: 3 })).informational).toBe(true);
    expect(withSnooze(row('key', { count: 4 })).informational).toBe(false);
  });

  it('should count the row again after a week', async () => {
    const { withSnooze } = snooze();
    run(withSnooze(row('key')), 'remind-later');

    await vi.advanceTimersByTimeAsync(WEEK_MS - 60_000);
    expect(withSnooze(row('key')).informational).toBe(true);

    await vi.advanceTimersByTimeAsync(60_000);
    expect(withSnooze(row('key')).informational).toBe(false);
  });

  it('should bring a snoozed row back at once when asked, and report the change', () => {
    const { onSnoozeChange, withSnooze } = snooze();
    const changed = vi.fn<(change: SetAsideChange) => void>();
    run(withSnooze(row('key')), 'remind-later');
    onSnoozeChange(changed);

    run(withSnooze(row('key')), 'remind-now');

    expect(withSnooze(row('key')).informational).toBe(false);
    expect(changed).toHaveBeenCalledWith({ from: SetAside.SNOOZED, id: 'key' });
  });

  it('should report a snoozed row being muted as coming from a snooze', () => {
    const { onSnoozeChange, withSnooze } = snooze();
    const changed = vi.fn<(change: SetAsideChange) => void>();
    run(withSnooze(row('key')), 'remind-later');
    onSnoozeChange(changed);

    run(withSnooze(row('key')), 'mute');

    expect(changed).toHaveBeenCalledWith({ from: SetAside.SNOOZED, id: 'key' });
  });

  it('should keep each user\'s snoozes apart', async () => {
    const { withSnooze } = snooze();
    run(withSnooze(row('key')), 'remind-later');
    await nextTick();

    set(useLoggedUserIdentifier(), 'bob');
    await nextTick();

    expect(withSnooze(row('key')).informational).toBe(false);
  });
});
