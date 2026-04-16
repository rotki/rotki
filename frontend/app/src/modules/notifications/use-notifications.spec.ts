import { Severity } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useNotifications } from '@/modules/notifications/use-notifications';

const mockNotify = vi.fn();
const mockSetMessage = vi.fn();
const mockRemoveMatching = vi.fn();

vi.mock('@/modules/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: vi.fn((): { notify: typeof mockNotify } => ({
    notify: mockNotify,
  })),
}));

vi.mock('@/modules/notifications/use-notifications-store', () => ({
  useNotificationsStore: vi.fn((): { removeMatching: typeof mockRemoveMatching } => ({
    removeMatching: mockRemoveMatching,
  })),
}));

vi.mock('@/modules/common/use-message-store', () => ({
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
      display: true,
      message: 'Error message',
      severity: Severity.ERROR,
      title: 'Error Title',
    });
  });

  it('should call notify with WARNING severity for notifyWarning', () => {
    const { notifyWarning } = useNotifications();
    notifyWarning('Warn Title', 'Warn message');

    expect(mockNotify).toHaveBeenCalledWith({
      display: true,
      message: 'Warn message',
      severity: Severity.WARNING,
      title: 'Warn Title',
    });
  });

  it('should call notify with INFO severity for notifyInfo', () => {
    const { notifyInfo } = useNotifications();
    notifyInfo('Info Title', 'Info message');

    expect(mockNotify).toHaveBeenCalledWith({
      display: true,
      message: 'Info message',
      severity: Severity.INFO,
      title: 'Info Title',
    });
  });

  it('should default display to true', () => {
    const { notifyError } = useNotifications();
    notifyError('Title', 'Message');

    expect(mockNotify).toHaveBeenCalledWith(
      expect.objectContaining({ display: true }),
    );
  });

  it('should allow overriding display to false', () => {
    const { notifyError } = useNotifications();
    notifyError('Title', 'Message', { display: false });

    expect(mockNotify).toHaveBeenCalledWith(
      expect.objectContaining({ display: false }),
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
