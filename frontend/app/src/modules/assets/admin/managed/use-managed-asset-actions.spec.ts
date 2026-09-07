import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type Ref, ref, shallowRef } from 'vue';
import { IgnoredAssetHandlingType, type IgnoredAssetsHandlingType } from '@/modules/assets/types';
import { useManagedAssetActions } from './use-managed-asset-actions';

let ignoredHandling: Ref<IgnoredAssetsHandlingType>;
let selected: Ref<string[]>;
let onIgnoredStale: ReturnType<typeof vi.fn<() => void>>;
let scope: ReturnType<typeof effectScope>;

function actions(): ReturnType<typeof useManagedAssetActions> {
  scope = effectScope();
  return scope.run(() => useManagedAssetActions({ ignoredHandling, onIgnoredStale, selected }))!;
}

describe('modules/assets/admin/managed/useManagedAssetActions', () => {
  beforeEach(() => {
    ignoredHandling = shallowRef<IgnoredAssetsHandlingType>(IgnoredAssetHandlingType.NONE);
    selected = ref<string[]>(['eip155:1/erc20:0xABC']);
    onIgnoredStale = vi.fn<() => void>();
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('which ignore actions are offered', () => {
    it('should offer both while ignored assets are shown alongside the rest', () => {
      const { disabledIgnoreActions } = actions();

      expect(get(disabledIgnoreActions)).toEqual({ ignore: false, unIgnore: false });
    });

    it('should not offer ignoring while only ignored assets are shown', () => {
      set(ignoredHandling, IgnoredAssetHandlingType.SHOW_ONLY);

      const { disabledIgnoreActions } = actions();

      expect(get(disabledIgnoreActions)).toEqual({ ignore: true, unIgnore: false });
    });

    it('should not offer un-ignoring while ignored assets are excluded', () => {
      set(ignoredHandling, IgnoredAssetHandlingType.EXCLUDE);

      const { disabledIgnoreActions } = actions();

      expect(get(disabledIgnoreActions)).toEqual({ ignore: false, unIgnore: true });
    });

    it('should follow a change of handling', async () => {
      const { disabledIgnoreActions } = actions();
      set(ignoredHandling, IgnoredAssetHandlingType.SHOW_ONLY);
      await flushPromises();

      expect(get(disabledIgnoreActions).ignore).toBe(true);
    });
  });

  describe('keeping the ignored list fresh', () => {
    it('should ask for it when the table switches to showing only ignored assets', async () => {
      actions();
      set(ignoredHandling, IgnoredAssetHandlingType.SHOW_ONLY);
      await flushPromises();

      expect(onIgnoredStale).toHaveBeenCalledOnce();
    });

    it('should not ask for it on any other handling', async () => {
      actions();
      set(ignoredHandling, IgnoredAssetHandlingType.EXCLUDE);
      await flushPromises();

      expect(onIgnoredStale).not.toHaveBeenCalled();
    });

    it('should not ask for it before the handling changes', () => {
      set(ignoredHandling, IgnoredAssetHandlingType.SHOW_ONLY);
      actions();

      expect(onIgnoredStale).not.toHaveBeenCalled();
    });
  });

  describe('the selection', () => {
    it('should clear it', () => {
      const { clearSelection } = actions();
      clearSelection();

      expect(get(selected)).toEqual([]);
    });
  });
});
