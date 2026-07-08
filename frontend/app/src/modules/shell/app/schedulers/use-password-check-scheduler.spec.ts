import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePasswordCheckScheduler } from './use-password-check-scheduler';

interface SchedulerOptions {
  callback: () => void;
  intervalMs: number;
}

let capturedOptions: SchedulerOptions | undefined;
const schedulerStart = vi.fn();
const schedulerStop = vi.fn();

const logged = ref<boolean>(false);
const username = ref<string>('');
const checkIfPasswordConfirmationNeeded = vi.fn().mockResolvedValue(undefined);

vi.mock('./use-interval-scheduler', () => ({
  useIntervalScheduler: (options: SchedulerOptions): object => {
    capturedOptions = options;
    return { start: schedulerStart, stop: schedulerStop };
  },
}));

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: (): object => ({ logged, username }),
}));

vi.mock('@/modules/auth/use-password-confirmation', () => ({
  usePasswordConfirmation: (): object => ({ checkIfPasswordConfirmationNeeded }),
}));

describe('usePasswordCheckScheduler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedOptions = undefined;
    set(logged, false);
    set(username, '');
  });

  it('should poll hourly', () => {
    usePasswordCheckScheduler();
    expect(capturedOptions?.intervalMs).toBe(60 * 60 * 1000);
  });

  it('should check the password when logged in with a username', () => {
    set(logged, true);
    set(username, 'alice');
    usePasswordCheckScheduler();
    capturedOptions?.callback();
    expect(checkIfPasswordConfirmationNeeded).toHaveBeenCalledWith('alice');
  });

  it('should do nothing when not logged in', () => {
    set(logged, false);
    set(username, 'alice');
    usePasswordCheckScheduler();
    capturedOptions?.callback();
    expect(checkIfPasswordConfirmationNeeded).not.toHaveBeenCalled();
  });

  it('should do nothing when there is no username', () => {
    set(logged, true);
    set(username, '');
    usePasswordCheckScheduler();
    capturedOptions?.callback();
    expect(checkIfPasswordConfirmationNeeded).not.toHaveBeenCalled();
  });

  it('should delegate start and stop to the interval scheduler', () => {
    const { start, stop } = usePasswordCheckScheduler();
    start();
    expect(schedulerStart).toHaveBeenCalledOnce();
    stop();
    expect(schedulerStop).toHaveBeenCalledOnce();
  });
});
