import type { BankAuthChallenge } from '@/modules/banks/types';
import { withSetup } from '@test/utils/with-setup';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useBankAuthenticationPolling } from '@/modules/banks/use-bank-authentication-polling';

const appApproval: BankAuthChallenge = {
  challenge: 'Approve in the app',
  challengeData: null,
  challengeHtml: null,
  challengeMimeType: null,
  pollDelaySeconds: 2,
  primitive: 'app approval poll',
  prompt: 'Approve in the app',
};

describe('useBankAuthenticationPolling', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('should poll at each delay returned by the bank until approval completes', async () => {
    vi.useFakeTimers();
    const challenge = ref<BankAuthChallenge | undefined>(appApproval);
    const poll = vi.fn<() => Promise<void>>()
      .mockImplementationOnce(async (): Promise<void> => set(challenge, { ...appApproval, pollDelaySeconds: 3 }))
      .mockImplementationOnce(async (): Promise<void> => set(challenge, undefined));
    const { result: polling } = withSetup(() => useBankAuthenticationPolling(challenge, poll));

    expect(get(polling)).toBe(true);
    await vi.advanceTimersByTimeAsync(2000);
    expect(poll).toHaveBeenCalledOnce();
    expect(get(polling)).toBe(true);

    await vi.advanceTimersByTimeAsync(2999);
    expect(poll).toHaveBeenCalledOnce();
    await vi.advanceTimersByTimeAsync(1);
    expect(poll).toHaveBeenCalledTimes(2);
    expect(get(polling)).toBe(false);
  });
});
