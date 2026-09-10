import type { DatabaseUploadProgress, DbUploadResult } from '@/modules/core/messaging/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref, shallowRef } from 'vue';
import { SYNC_UPLOAD, type SyncAction } from '@/modules/session/sync';
import SyncIndicator from '@/modules/shell/cloud-sync/SyncIndicator.vue';
import ConfirmDialog from '@/modules/shell/components/dialogs/ConfirmDialog.vue';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';

let cloudBackupAllowed: Ref<boolean>;
let syncAction: Ref<SyncAction | undefined>;
let uploadProgress: Ref<DatabaseUploadProgress | undefined>;
let uploadStatus: Ref<DbUploadResult | null>;
let displaySyncConfirmation: Ref<boolean>;
let confirmChecked: Ref<boolean>;
let isSyncing: Ref<boolean>;
let premium: Ref<boolean>;

const { cancelSync, forceSync, showSyncConfirmation } = vi.hoisted(() => ({
  cancelSync: vi.fn(),
  forceSync: vi.fn(async () => Promise.resolve()),
  showSyncConfirmation: vi.fn(),
}));

vi.mock('@/modules/session/use-session-sync', () => ({
  useSync: (): Record<string, unknown> => ({
    cancelSync,
    clearUploadStatus: vi.fn(),
    confirmChecked,
    displaySyncConfirmation,
    forceSync,
    showSyncConfirmation,
    syncAction,
    uploadProgress,
    uploadStatus,
  }),
}));

vi.mock('@/modules/premium/use-feature-access', async () => {
  const actual = await vi.importActual<typeof import('@/modules/premium/use-feature-access')>(
    '@/modules/premium/use-feature-access',
  );
  return {
    ...actual,
    useFeatureAccess: (): Record<string, unknown> => ({ allowed: cloudBackupAllowed }),
  };
});

vi.mock('@/modules/premium/use-premium-store', () => ({
  usePremiumStore: (): Record<string, unknown> => ({
    premium,
    premiumSync: ref<boolean>(false),
  }),
}));

vi.mock('@/modules/session/use-session-metadata-store', () => ({
  useSessionMetadataStore: (): Record<string, unknown> => ({
    lastDataUpload: ref<number>(),
  }),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): Record<string, unknown> => ({ cancelActivity: vi.fn() }),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({ useIsActive: (): Ref<boolean> => isSyncing }),
}));

vi.mock('@/modules/auth/use-logout', () => ({
  useLogout: (): Record<string, unknown> => ({ logout: vi.fn() }),
}));

vi.mock('@/modules/shell/layout/use-links', () => ({
  useLinks: (): Record<string, unknown> => ({ href: ref('https://rotki.com'), onLinkClick: vi.fn() }),
}));

function createWrapper(): VueWrapper {
  return mount(SyncIndicator, {
    global: {
      plugins: [createCustomPinia()],
      stubs: {
        AskUserUponSizeDiscrepancySetting: true,
        ConfirmDialog: true,
        DateDisplay: true,
        MenuTooltipButton: true,
        SyncButtons: true,
        SyncSettings: true,
        SyncUploadStatusAlert: true,
      },
    },
  });
}

describe('modules/shell/cloud-sync/SyncIndicator.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    cloudBackupAllowed = ref<boolean>(true);
    syncAction = shallowRef<SyncAction>(SYNC_UPLOAD);
    uploadProgress = ref<DatabaseUploadProgress>();
    uploadStatus = ref<DbUploadResult | null>(null);
    displaySyncConfirmation = ref<boolean>(false);
    confirmChecked = ref<boolean>(false);
    isSyncing = ref<boolean>(false);
    premium = ref<boolean>(true);
  });

  it('should keep the confirmed action disabled until the box is ticked', async () => {
    const wrapper = createWrapper();
    const dialog = wrapper.findComponent(ConfirmDialog);

    expect(dialog.props('disabled')).toBe(true);

    set(confirmChecked, true);
    await flushPromises();

    expect(dialog.props('disabled')).toBe(false);
  });

  it('should sync nothing while the dialog only sits there', () => {
    createWrapper();

    expect(forceSync).not.toHaveBeenCalled();
  });

  it('should sync when the dialog is confirmed', async () => {
    const wrapper = createWrapper();

    wrapper.findComponent(ConfirmDialog).vm.$emit('confirm');
    await flushPromises();

    expect(forceSync).toHaveBeenCalledOnce();
  });

  it('should sync nothing when the dialog is cancelled', async () => {
    const wrapper = createWrapper();

    wrapper.findComponent(ConfirmDialog).vm.$emit('cancel');
    await flushPromises();

    expect(cancelSync).toHaveBeenCalledOnce();
    expect(forceSync).not.toHaveBeenCalled();
  });

  it('should offer the upgrade link instead of the menu without premium', () => {
    set(premium, false);

    const wrapper = createWrapper();

    expect(wrapper.find('#balances-saved-dropdown').exists()).toBe(false);
    expect(wrapper.findComponent(MenuTooltipButton).props('tooltip')).toBe('sync_indicator.menu_tooltip');
  });

  it('should offer the menu with premium', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('#balances-saved-dropdown').exists()).toBe(true);
  });
});
