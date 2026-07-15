import { describe, expect, it } from 'vitest';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import { actionEntries, actionKeysForAnchor, anchorId, getActionEntry, settingsActions } from '@/modules/settings/settings-actions';
import { getRegistryEntry } from '@/modules/settings/settings-registry';

describe('settingsActions', () => {
  it('should resolve an action anchor id from an action key', () => {
    const anchor = getActionEntry('purgeData')?.anchor;
    expect(anchor).toBeDefined();
    expect(anchorId('purgeData')).toBe(anchor);
  });

  it('should resolve a setting anchor id from a registry key (cross-registry)', () => {
    const anchor = getRegistryEntry('autoDetectTokens')?.anchor;
    expect(anchor).toBeDefined();
    expect(anchorId('autoDetectTokens')).toBe(anchor);
  });

  it('should return no anchor id for an info action that has no scroll target', () => {
    expect(getActionEntry('latestPrices')?.anchor).toBeUndefined();
    expect(anchorId('latestPrices')).toBeUndefined();
  });

  it('should reverse-index an anchor back to its owning action key', () => {
    expect(actionKeysForAnchor(SettingsHighlightIds.PURGE_DATA)).toEqual(['purgeData']);
  });

  it('should not own an anchor that belongs to a registry setting', () => {
    expect(actionKeysForAnchor(SettingsHighlightIds.AUTO_DETECT_TOKENS)).toEqual([]);
  });

  it('should expose every action as a typed entry pair', () => {
    const keys = actionEntries().map(([key]) => key);
    expect(keys).toEqual(Object.keys(settingsActions));
  });
});
