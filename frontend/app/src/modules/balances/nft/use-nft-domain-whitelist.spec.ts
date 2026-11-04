import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useNftDomainWhitelist } from './use-nft-domain-whitelist';

const { show, updateFrontendSetting, whitelisted } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    show: vi.fn<(content: object, onConfirm: () => void) => void>(),
    updateFrontendSetting: vi.fn<(payload: object) => Promise<{ success: boolean }>>(async () => Promise.resolve({ success: true })),
    whitelisted: ref<string[]>(['existing.io']),
  };
});

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): object => ({ show }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => whitelisted),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): object => ({ updateFrontendSetting }),
}));

function confirm(): void {
  const onConfirm = show.mock.calls[0][1];
  onConfirm();
}

describe('useNftDomainWhitelist', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(whitelisted, ['existing.io']);
  });

  it('should name the registrable domain the media is served from', () => {
    const { domain } = useNftDomainWhitelist('https://www.images.example.com/nft/1.png');
    expect(get(domain)).toBe('example.com');
  });

  it('should add the domain to the whitelist only once the user confirms', () => {
    const { confirmAllowDomain } = useNftDomainWhitelist('https://cdn.example.com/1.png');
    confirmAllowDomain();
    expect(updateFrontendSetting).not.toHaveBeenCalled();

    confirm();
    expect(updateFrontendSetting).toHaveBeenCalledWith({
      whitelistedDomainsForNftImages: ['existing.io', 'example.com'],
    });
  });

  it('should not list an already allowed domain twice', () => {
    const { confirmAllowDomain } = useNftDomainWhitelist('https://existing.io/1.png');
    confirmAllowDomain();
    confirm();
    expect(updateFrontendSetting).toHaveBeenCalledWith({ whitelistedDomainsForNftImages: ['existing.io'] });
  });

  it('should leave the whitelist alone when there is no media URL', () => {
    const { confirmAllowDomain } = useNftDomainWhitelist(null);
    confirmAllowDomain();
    confirm();
    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });
});
