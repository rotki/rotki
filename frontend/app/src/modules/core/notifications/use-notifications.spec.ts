import { Priority, Severity } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

const mockNotify = vi.fn();
const mockSetMessage = vi.fn();
const mockRemoveMatching = vi.fn();

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: vi.fn((): { notify: typeof mockNotify } => ({
    notify: mockNotify,
  })),
}));

vi.mock('@/modules/core/notifications/use-notifications-store', () => ({
  useNotificationsStore: vi.fn((): { removeMatching: typeof mockRemoveMatching } => ({
    removeMatching: mockRemoveMatching,
  })),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: vi.fn((): { setMessage: typeof mockSetMessage } => ({
    setMessage: mockSetMessage,
  })),
}));

describe('useNotifications', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call notify with ERROR severity for notifyError', () => {
    const { notifyError } = useNotifications();
    notifyError('Error Title', 'Error message');

    expect(mockNotify).toHaveBeenCalledWith({
      message: 'Error message',
      severity: Severity.ERROR,
      title: 'Error Title',
    });
  });

  it('should call notify with WARNING severity for notifyWarning', () => {
    const { notifyWarning } = useNotifications();
    notifyWarning('Warn Title', 'Warn message');

    expect(mockNotify).toHaveBeenCalledWith({
      message: 'Warn message',
      severity: Severity.WARNING,
      title: 'Warn Title',
    });
  });

  it('should call notify with INFO severity for notifyInfo', () => {
    const { notifyInfo } = useNotifications();
    notifyInfo('Info Title', 'Info message');

    expect(mockNotify).toHaveBeenCalledWith({
      message: 'Info message',
      severity: Severity.INFO,
      title: 'Info Title',
    });
  });

  it('should never decide display itself, leaving it to the dispatcher', () => {
    const { notifyError } = useNotifications();
    notifyError('Title', 'Message');

    expect(mockNotify).toHaveBeenCalledWith(
      expect.not.objectContaining({ display: expect.anything() }),
    );
  });

  it('should forward a classifying priority so the caller can opt out of a popup', () => {
    const { notifyError } = useNotifications();
    notifyError('Title', 'Message', { priority: Priority.NORMAL });

    expect(mockNotify).toHaveBeenCalledWith(
      expect.objectContaining({ priority: Priority.NORMAL }),
    );
  });

  it('should call setMessage with success true for showSuccessMessage', () => {
    const { showSuccessMessage } = useNotifications();
    showSuccessMessage('Success Title', 'Success description');

    expect(mockSetMessage).toHaveBeenCalledWith({
      description: 'Success description',
      success: true,
      title: 'Success Title',
    });
  });

  it('should call setMessage with success false for showErrorMessage', () => {
    const { showErrorMessage } = useNotifications();
    showErrorMessage('Error Title', 'Error description');

    expect(mockSetMessage).toHaveBeenCalledWith({
      description: 'Error description',
      success: false,
      title: 'Error Title',
    });
  });
});
