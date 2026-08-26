import { describe, expect, it } from 'vitest';
import { managedAssetStatusParams } from '@/modules/assets/admin/managed/use-assets-filter';
import { IgnoredAssetHandlingType, type IgnoredAssetsHandlingType } from '@/modules/assets/types';

function setup(
  handling: IgnoredAssetsHandlingType = IgnoredAssetHandlingType.EXCLUDE,
  owned = false,
  whitelisted = false,
): {
  status: { ignoredAssetsHandling: Ref<IgnoredAssetsHandlingType>; onlyShowOwned: Ref<boolean>; onlyShowWhitelisted: Ref<boolean> };
  params: ReturnType<typeof managedAssetStatusParams>;
} {
  const status = {
    ignoredAssetsHandling: ref<IgnoredAssetsHandlingType>(handling),
    onlyShowOwned: ref<boolean>(owned),
    onlyShowWhitelisted: ref<boolean>(whitelisted),
  };
  return { params: managedAssetStatusParams(status), status };
}

describe('managedAssetStatusParams', () => {
  it('should send the two flags to the request as booleans, not as the strings a pill carries', () => {
    const { params } = setup(IgnoredAssetHandlingType.EXCLUDE, true, false);

    expect(toValue(params.source.values)).toStrictEqual({
      ignoredAssetsHandling: IgnoredAssetHandlingType.EXCLUDE,
      showUserOwnedAssetsOnly: true,
      showWhitelistedAssetsOnly: false,
    });
  });

  // The backend needs the handling stated even when no pill says it, which is the one way the
  // source and the bar's bag differ.
  it('should state the default handling in the request', () => {
    const { params } = setup();

    expect(toValue(params.source.values)).toHaveProperty(
      'ignoredAssetsHandling',
      IgnoredAssetHandlingType.EXCLUDE,
    );
  });

  it('should draw no pill for anything at its default', () => {
    const { params } = setup();

    expect(get(params.pillParams)).toStrictEqual({});
  });

  it('should draw a pill for each departure from the default', () => {
    const { params } = setup(IgnoredAssetHandlingType.SHOW_ONLY, true, true);

    expect(get(params.pillParams)).toStrictEqual({
      ignoredAssetsHandling: IgnoredAssetHandlingType.SHOW_ONLY,
      showUserOwnedAssetsOnly: true,
      showWhitelistedAssetsOnly: true,
    });
  });

  it('should write the refs back from the bar\'s bag', () => {
    const { params, status } = setup();

    set(params.pillParams, {
      ignoredAssetsHandling: IgnoredAssetHandlingType.SHOW_ONLY,
      showUserOwnedAssetsOnly: true,
    });

    expect(get(status.ignoredAssetsHandling)).toBe(IgnoredAssetHandlingType.SHOW_ONLY);
    expect(get(status.onlyShowOwned)).toBe(true);
    expect(get(status.onlyShowWhitelisted)).toBe(false);
  });

  // Removing a pill is how a filter is turned off, and for the handling "off" is the default.
  it('should return to the defaults when the pills are cleared', () => {
    const { params, status } = setup(IgnoredAssetHandlingType.SHOW_ONLY, true, true);

    set(params.pillParams, {});

    expect(get(status.ignoredAssetsHandling)).toBe(IgnoredAssetHandlingType.EXCLUDE);
    expect(get(status.onlyShowOwned)).toBe(false);
    expect(get(status.onlyShowWhitelisted)).toBe(false);
  });

  it('should restore all three from the url', () => {
    const { params, status } = setup();

    params.source.fromQuery?.({
      ignoredAssetsHandling: IgnoredAssetHandlingType.SHOW_ONLY,
      showUserOwnedAssetsOnly: 'true',
      showWhitelistedAssetsOnly: 'false',
    });

    expect(get(status.ignoredAssetsHandling)).toBe(IgnoredAssetHandlingType.SHOW_ONLY);
    expect(get(status.onlyShowOwned)).toBe(true);
    expect(get(status.onlyShowWhitelisted)).toBe(false);
  });

  // A url is anyone's to write, and the handling reaches the request and the pill's label alike.
  it('should fall back on a handling the backend does not take', () => {
    const { params, status } = setup(IgnoredAssetHandlingType.SHOW_ONLY);

    params.source.fromQuery?.({ ignoredAssetsHandling: 'nonsense' });

    expect(get(status.ignoredAssetsHandling)).toBe(IgnoredAssetHandlingType.EXCLUDE);
  });

  it('should ride both the request and the url', () => {
    expect(setup().params.source.to).toBe('both');
  });
});
