import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useAssetUpdateThrottle } from './use-asset-update-throttle';

function setVersion(version: string): void {
  set(storeToRefs(useMainStore()).version, { downloadUrl: '', latestVersion: '', version });
}

describe('useAssetUpdateThrottle', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    setVersion('1.0.0');
  });

  it('should check on the first login when nothing was recorded', () => {
    expect(useAssetUpdateThrottle().shouldCheck()).toBe(true);
  });

  it('should not check again the same day on the same version', () => {
    const throttle = useAssetUpdateThrottle();
    throttle.recordCheck();
    expect(throttle.shouldCheck()).toBe(false);
  });

  it('should check again after the app version changes', () => {
    const throttle = useAssetUpdateThrottle();
    throttle.recordCheck();
    setVersion('1.1.0');
    expect(throttle.shouldCheck()).toBe(true);
  });

  it('should check again when the recorded day is stale', () => {
    localStorage.setItem('rotki.asset_update_check.day', '2000-01-01');
    localStorage.setItem('rotki.asset_update_check.version', '1.0.0');
    expect(useAssetUpdateThrottle().shouldCheck()).toBe(true);
  });
});
