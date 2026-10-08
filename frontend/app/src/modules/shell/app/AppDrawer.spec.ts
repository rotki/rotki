import { resetOverlayStack, useOverlayStack } from '@rotki/ui-library';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import AppDrawer from '@/modules/shell/app/AppDrawer.vue';

const { isXlAndDown } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { isXlAndDown: ref<boolean>(true) };
});

vi.mock('@rotki/ui-library', async (importActual) => {
  const actual = await importActual<typeof import('@rotki/ui-library')>();
  return { ...actual, useBreakpoint: (): Record<string, unknown> => ({ isXlAndDown }) };
});

function createWrapper(): VueWrapper<InstanceType<typeof AppDrawer>> {
  return mount(AppDrawer, {
    global: {
      stubs: {
        GlobalSearch: true,
        NavigationMenu: true,
        RotkiLogo: true,
        RouterLink: { template: '<a><slot /></a>' },
        RuiNavigationDrawer: { template: '<div><slot /></div>' },
        SponsorshipView: true,
      },
    },
  });
}

describe('modules/shell/app/AppDrawer', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    resetOverlayStack();
  });

  describe('dismissed from the overlay stack, as the back gesture does', () => {
    it('should close the drawer while it slides over the page', () => {
      set(isXlAndDown, true);
      const { showDrawer } = storeToRefs(useAreaVisibilityStore());
      set(showDrawer, true);
      createWrapper();

      expect(useOverlayStack().dismissTop()).toBe(true);
      expect(get(showDrawer)).toBe(false);
    });

    it('should leave nothing to dismiss while the drawer is closed', () => {
      set(isXlAndDown, true);
      set(storeToRefs(useAreaVisibilityStore()).showDrawer, false);
      createWrapper();

      expect(useOverlayStack().dismissTop()).toBe(false);
    });

    it('should leave nothing to dismiss when the drawer is docked beside the page', () => {
      set(isXlAndDown, false);
      const { showDrawer } = storeToRefs(useAreaVisibilityStore());
      createWrapper();

      expect(get(showDrawer)).toBe(true);
      expect(useOverlayStack().dismissTop()).toBe(false);
      expect(get(showDrawer)).toBe(true);
    });
  });
});
