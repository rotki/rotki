<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import { TaskType } from '@/types/task-type';
import {
  SYNC_DOWNLOAD,
  SYNC_UPLOAD,
  type SyncAction
} from '@/types/session/sync';

const { t } = useI18n();
const { logout } = useSessionStore();
const { lastDataUpload } = storeToRefs(usePeriodicStore());
const {
  confirmChecked,
  displaySyncConfirmation,
  syncAction,
  cancelSync,
  forceSync,
  showSyncConfirmation
} = useSync();
const { href, onLinkClick } = useLinks();

const premium = usePremium();

const pending = ref<boolean>(false);
const visible = ref<boolean>(false);

const isDownload = computed<boolean>(() => get(syncAction) === SYNC_DOWNLOAD);
const textChoice = computed<number>(() =>
  get(syncAction) === SYNC_UPLOAD ? 1 : 2
);
const message = computed<string>(() =>
  get(syncAction) === SYNC_UPLOAD
    ? t('sync_indicator.upload_confirmation.message_upload').toString()
    : t('sync_indicator.upload_confirmation.message_download').toString()
);

const { resume, pause, counter } = useInterval(600, {
  immediate: false,
  controls: true
});

const icon = computed(() => {
  const tick = get(counter) % 2 === 0;
  if (get(isDownload)) {
    return tick ? 'download-cloud-2-line' : 'download-cloud-line';
  }
  return tick ? 'upload-cloud-2-line' : 'upload-cloud-line';
});

const showConfirmation = (action: SyncAction) => {
  set(visible, false);
  showSyncConfirmation(action);
};

const actionLogout = async () => {
  await logout();
  await navigateToUserLogin();
};

const performSync = async () => {
  resume();
  set(pending, true);
  await forceSync(actionLogout);
  set(pending, false);
  pause();
};

const { isTaskRunning } = useTaskStore();
const isSyncing = isTaskRunning(TaskType.FORCE_SYNC);

watch(isSyncing, (current, prev) => {
  if (current !== prev && !current) {
    cancelSync();
  }
});

const { navigateToUserLogin } = useAppNavigation();
</script>

<template>
  <Fragment>
    <template v-if="premium">
      <VMenu
        id="balances-saved-dropdown"
        v-model="visible"
        transition="slide-y-transition"
        offset-y
        :close-on-content-click="false"
        z-index="215"
      >
        <template #activator="{ on }">
          <MenuTooltipButton
            :tooltip="t('sync_indicator.menu_tooltip')"
            class-name="secondary--text text--lighten-4"
            :on-menu="on"
          >
            <RuiIcon v-if="isSyncing" :name="icon" color="primary" />
            <RuiIcon v-else name="cloud-line" />
          </MenuTooltipButton>
        </template>
        <div class="pa-4 md:w-[250px] w-full">
          <div class="font-medium">
            {{ t('sync_indicator.last_data_upload') }}
          </div>
          <div class="py-2 text--secondary">
            <DateDisplay v-if="lastDataUpload" :timestamp="lastDataUpload" />
            <span v-else>
              {{ t('common.never') }}
            </span>
          </div>
          <SyncButtons :pending="pending" @action="showConfirmation($event)" />
        </div>
      </VMenu>
    </template>
    <template v-else>
      <RuiBadge
        placement="top"
        offset-y="12"
        offset-x="-10"
        size="sm"
        color="default"
      >
        <template #icon>
          <RuiIcon name="lock-line" color="primary" size="14" />
        </template>
        <MenuTooltipButton
          :tooltip="t('sync_indicator.menu_tooltip')"
          class-name="secondary--text text--lighten-4"
          :href="href"
          @click="onLinkClick()"
        >
          <RuiIcon name="cloud-line" />
        </MenuTooltipButton>
      </RuiBadge>
    </template>

    <ConfirmDialog
      confirm-type="warning"
      :display="displaySyncConfirmation"
      :title="t('sync_indicator.upload_confirmation.title', textChoice)"
      :message="message"
      :disabled="!confirmChecked"
      :primary-action="
        t('sync_indicator.upload_confirmation.action', textChoice)
      "
      :loading="isSyncing"
      :secondary-action="t('common.actions.cancel')"
      @cancel="cancelSync()"
      @confirm="performSync()"
    >
      <div
        v-if="isDownload"
        class="font-medium mt-3"
        v-text="
          t('sync_indicator.upload_confirmation.message_download_relogin')
        "
      />
      <RuiCheckbox v-model="confirmChecked" color="primary">
        {{ t('sync_indicator.upload_confirmation.confirm_check') }}
      </RuiCheckbox>
    </ConfirmDialog>
  </Fragment>
</template>
