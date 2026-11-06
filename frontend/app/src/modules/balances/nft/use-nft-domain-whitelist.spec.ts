import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useNftDomainWhitelist } from './use-nft-domain-whitelist';

const { updateFrontendSetting, whitelisted } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    updateFrontendSetting: vi.fn<(payload: object) => Promise<{ success: boolean }>>(async () => Promise.resolve({ success: true })),
    whitelisted: ref<string[]>(['existing.io']),
  };
});

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => whitelisted),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): object => ({ updateFrontendSetting }),
}));

describe('useNftDomainWhitelist', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(whitelisted, ['existing.io']);
  });

  it('should name the registrable domain the media is served from', () => {
    const { domain } = useNftDomainWhitelist('https://www.images.example.com/nft/1.png');
    expect(get(domain)).toBe('example.com');
  });

  it('should name the domain in the question asked before allowing it', () => {
    const { question } = useNftDomainWhitelist('https://cdn.example.com/1.png');
    expect(get(question).message).toBe('general_settings.nft_setting.update_whitelist_confirmation.message::example.com');
    expect(get(question).confirmLabel).toBe('general_settings.nft_setting.update_whitelist_confirmation.confirm');
  });

  it('should add the domain to the whitelist', () => {
    const { allowDomain } = useNftDomainWhitelist('https://cdn.example.com/1.png');
    allowDomain();
    expect(updateFrontendSetting).toHaveBeenCalledWith({
      whitelistedDomainsForNftImages: ['existing.io', 'example.com'],
    });
  });

  it('should not list an already allowed domain twice', () => {
    const { allowDomain } = useNftDomainWhitelist('https://existing.io/1.png');
    allowDomain();
    expect(updateFrontendSetting).toHaveBeenCalledWith({ whitelistedDomainsForNftImages: ['existing.io'] });
  });

  it('should leave the whitelist alone when there is no media URL', () => {
    const { allowDomain } = useNftDomainWhitelist(null);
    allowDomain();
    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });
});
