import type { Router } from 'vue-router';
import type { CalendarEventWithReminder } from '@/modules/calendar/types';
import { NotificationCategory, Severity } from '@rotki/common';
import { mockT } from '@test/i18n';
import { createMock } from '@test/utils/create-mock';
import dayjs from 'dayjs';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';
import relativeTime from 'dayjs/plugin/relativeTime';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { createCalendarReminderHandler } from '@/modules/core/messaging/handlers/calendar-reminder';

dayjs.extend(isSameOrAfter);
dayjs.extend(relativeTime);

const mockGetChainName = vi.fn((chain: string): string => chain.toUpperCase());
const mockGetAddressName = vi.fn();
const mockRemoveMatching = vi.fn();
const mockEditCalendarReminder = vi.fn();
const mockPush = vi.fn();

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getChainName: mockGetChainName,
  })),
}));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: vi.fn(() => ({
    getAddressName: mockGetAddressName,
  })),
}));

vi.mock('@/modules/core/notifications/use-notifications-store', () => ({
  useNotificationsStore: vi.fn(() => ({
    removeMatching: mockRemoveMatching,
  })),
}));

vi.mock('@/modules/calendar/use-calendar-reminder-api', () => ({
  useCalendarReminderApi: vi.fn(() => ({
    editCalendarReminder: mockEditCalendarReminder,
  })),
}));

const PAST = 1_000_000; // seconds — far in the past
const FUTURE = 9_999_999_999; // seconds — year 2286

function event(overrides: Partial<CalendarEventWithReminder> = {}): CalendarEventWithReminder {
  return createMock<CalendarEventWithReminder>({
    address: '',
    blockchain: '',
    counterparty: '',
    description: '',
    identifier: 7,
    name: 'Vesting unlock',
    reminder: { identifier: 3, secsBefore: 3600 },
    timestamp: PAST,
    ...overrides,
  });
}

const router = createMock<Router>({ push: mockPush });

describe('createCalendarReminderHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetChainName.mockImplementation((chain: string): string => chain.toUpperCase());
    mockGetAddressName.mockReturnValue(undefined);
    mockEditCalendarReminder.mockResolvedValue(undefined);
  });

  it('should remove any existing reminder for the same event', async () => {
    const handler = createCalendarReminderHandler(mockT, router);
    await handler.handle(event());

    expect(mockRemoveMatching).toHaveBeenCalledOnce();
  });

  it('should use the plain name once the event time has passed', async () => {
    const handler = createCalendarReminderHandler(mockT, router);
    const notification = await handler.handle(event({ name: 'Vesting unlock', timestamp: PAST }));

    expect(notification.title).toBe('Vesting unlock');
    expect(notification.category).toBe(NotificationCategory.CALENDAR_REMINDER);
    expect(notification.severity).toBe(Severity.REMINDER);
  });

  it('should prepend a relative time when the event is still upcoming', async () => {
    const handler = createCalendarReminderHandler(mockT, router);
    const notification = await handler.handle(event({ name: 'Vesting unlock', timestamp: FUTURE }));

    expect(notification.title).not.toBe('Vesting unlock');
    expect(notification.title).toContain('Vesting unlock');
  });

  it('should include the resolved account and chain in the message', async () => {
    mockGetAddressName.mockReturnValue('alice.eth');
    const handler = createCalendarReminderHandler(mockT, router);
    const notification = await handler.handle(event({ address: '0xabc', blockchain: 'eth' }));

    expect(notification.message).toContain('alice.eth');
    expect(notification.message).toContain('ETH');
  });

  it('should fall back to the raw address when no name resolves', async () => {
    mockGetAddressName.mockReturnValue(undefined);
    const handler = createCalendarReminderHandler(mockT, router);
    const notification = await handler.handle(event({ address: '0xabc', blockchain: 'eth' }));

    expect(notification.message).toContain('0xabc');
  });

  it('should include counterparty and description in the message', async () => {
    const handler = createCalendarReminderHandler(mockT, router);
    const notification = await handler.handle(event({ counterparty: 'uniswap', description: 'unlock tokens' }));

    expect(notification.message).toContain('uniswap');
    expect(notification.message).toContain('unlock tokens');
  });

  it('should acknowledge the reminder and open the calendar from the action', async () => {
    const handler = createCalendarReminderHandler(mockT, router);
    const notification = await handler.handle(event({ identifier: 7, timestamp: PAST }));

    assert(!Array.isArray(notification.action) && notification.action);
    await notification.action.action();

    expect(mockEditCalendarReminder).toHaveBeenCalledWith(expect.objectContaining({
      acknowledged: true,
      eventId: 7,
    }));
    expect(mockPush).toHaveBeenCalledWith({ path: '/calendar', query: { timestamp: PAST.toString() } });
  });
});
