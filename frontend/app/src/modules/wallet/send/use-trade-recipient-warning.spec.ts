import type { EffectScope, Ref } from 'vue';
import flushPromises from 'flush-promises';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useTradeRecipientWarning } from '@/modules/wallet/send/use-trade-recipient-warning';

const FROM = '0x9531C059098e3d194fF87FebB587aB07B30B1306';
const TO = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65';

const getIsInteractedBefore = vi.fn<(from: string, to: string) => Promise<boolean>>();

vi.mock('@/modules/wallet/send/use-trade-api', () => ({
  useTradeApi: vi.fn(() => ({ getIsInteractedBefore })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

describe('useTradeRecipientWarning', () => {
  let scope: EffectScope;
  let fromAddress: Ref<string | undefined>;
  let toAddress: Ref<string>;

  function create(): ReturnType<typeof useTradeRecipientWarning> {
    scope = effectScope();
    const result = scope.run(() => useTradeRecipientWarning({ fromAddress, toAddress }));
    assert(result);
    return result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    fromAddress = ref<string | undefined>(FROM);
    toAddress = ref<string>('');
    getIsInteractedBefore.mockResolvedValue(false);
  });

  afterEach(() => {
    scope.stop();
  });

  it('should warn about a recipient never transacted with', async () => {
    const { showNeverInteractedWarning } = create();

    set(toAddress, TO);
    await flushPromises();

    expect(getIsInteractedBefore).toHaveBeenCalledWith(FROM, TO);
    expect(get(showNeverInteractedWarning)).toBe(true);
  });

  it('should stay quiet for a known recipient', async () => {
    getIsInteractedBefore.mockResolvedValue(true);
    const { showNeverInteractedWarning } = create();

    set(toAddress, TO);
    await flushPromises();

    expect(get(showNeverInteractedWarning)).toBe(false);
  });

  it('should not ask about a half-typed address', async () => {
    const { showNeverInteractedWarning } = create();

    set(toAddress, '0xc37b40ABdB');
    await flushPromises();

    expect(getIsInteractedBefore).not.toHaveBeenCalled();
    expect(get(showNeverInteractedWarning)).toBe(false);
  });

  it('should not ask without a connected address', async () => {
    set(fromAddress, undefined);
    const { showNeverInteractedWarning } = create();

    set(toAddress, TO);
    await flushPromises();

    expect(getIsInteractedBefore).not.toHaveBeenCalled();
    expect(get(showNeverInteractedWarning)).toBe(false);
  });

  it('should withdraw the warning when the recipient is cleared', async () => {
    const { showNeverInteractedWarning } = create();
    set(toAddress, TO);
    await flushPromises();
    expect(get(showNeverInteractedWarning)).toBe(true);

    set(toAddress, '');
    await flushPromises();

    expect(get(showNeverInteractedWarning)).toBe(false);
  });

  it('should not raise a false alarm when the lookup fails', async () => {
    getIsInteractedBefore.mockRejectedValue(new Error('backend is down'));
    const { showNeverInteractedWarning } = create();

    set(toAddress, TO);
    await flushPromises();

    expect(get(showNeverInteractedWarning)).toBe(false);
  });
});
