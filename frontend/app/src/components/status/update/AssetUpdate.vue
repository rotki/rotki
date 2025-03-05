<script setup lang="ts">
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';
import { useMainStore } from '@/store/main';
import { useBackendManagement } from '@/composables/backend';
import { useRestartingStatus } from '@/composables/user/account';
import { useAssets } from '@/composables/assets';
import AssetConflictDialog from '@/components/status/update/AssetConflictDialog.vue';
import AssetUpdateMessage from '@/components/status/update/AssetUpdateMessage.vue';
import AssetUpdateInlineConfirm from '@/components/status/update/AssetUpdateInlineConfirm.vue';
import AssetUpdateStatus from '@/components/status/update/AssetUpdateStatus.vue';
import AssetUpdateSetting from '@/components/status/update/AssetUpdateSetting.vue';
import { useLogout } from '@/modules/account/use-logout';
import type { AssetUpdateConflictResult, AssetVersionUpdate, ConflictResolution } from '@/types/asset';

const props = withDefaults(defineProps<{ headless?: boolean }>(), {
  headless: false,
});

const emit = defineEmits<{ (e: 'skip'): void }>();

const { headless } = toRefs(props);
const checking = ref<boolean>(false);
const applying = ref<boolean>(false);
const inlineConfirm = ref<boolean>(false);
const showUpdateDialog = ref<boolean>(false);
const showConflictDialog = ref<boolean>(false);
const conflicts = ref<AssetUpdateConflictResult[]>([]);
const changes = ref<AssetVersionUpdate>({
  changes: 0,
  local: 0,
  remote: 0,
  upToVersion: 0,
});

const skipped = useLocalStorage('rotki_skip_asset_db_version', 0);

const status = computed(() => {
  if (get(checking))
    return 'checking';

  if (get(applying))
    return 'applying';

  return null;
});

const { logout } = useLogout();
const { applyUpdates, checkForUpdate } = useAssets();
const { connect, setConnected } = useMainStore();
const { restartBackend } = useBackendManagement();

const { t } = useI18n();
const { setMessage } = useMessageStore();

async function check() {
  set(checking, true);
  const checkResult = await checkForUpdate();
  set(checking, false);
  const skippedVersion = get(skipped);
  const versions = checkResult.versions;
  if (get(headless) && skippedVersion && skippedVersion === versions?.remote) {
    set(checking, false);
    emit('skip');
    return;
  }

  set(showUpdateDialog, checkResult.updateAvailable);

  if (!checkResult.updateAvailable) {
    if (get(headless)) {
      emit('skip');
    }
    else {
      setMessage({
        description: t('asset_update.up_to_date'),
        success: true,
      });
    }
  }

  if (versions) {
    set(changes, {
      changes: versions.newChanges,
      local: versions.local,
      remote: versions.remote,
      upToVersion: versions.remote,
    });
  }
}

function skip(skipUpdate: boolean) {
  set(showUpdateDialog, false);
  set(showConflictDialog, false);
  if (skipUpdate)
    set(skipped, get(changes).remote);

  emit('skip');
}

async function updateAssets(resolution?: ConflictResolution) {
  set(showUpdateDialog, false);
  set(showConflictDialog, false);
  const version = get(changes).upToVersion;
  set(applying, true);
  const updateResult = await applyUpdates({ resolution, version });
  set(applying, false);
  if (updateResult.done) {
    set(skipped, 0);
    showDoneConfirmation();
  }
  else if (updateResult.conflicts) {
    set(conflicts, updateResult.conflicts);
    set(showConflictDialog, true);
  }
}

const { restarting } = useRestartingStatus();

async function updateComplete() {
  if (get(restarting))
    return;

  set(restarting, true);
  await logout(true);
  setConnected(false);
  await restartBackend();
  await connect();
  set(restarting, false);
}

const { show } = useConfirmStore();

function showDoneConfirmation() {
  if (get(headless)) {
    set(inlineConfirm, true);
  }
  else {
    show(
      {
        message: t('asset_update.success.description', {
          remoteVersion: get(changes).upToVersion,
        }),
        primaryAction: t('common.actions.ok'),
        singleAction: true,
        title: t('asset_update.success.title'),
        type: 'success',
      },
      updateComplete,
    );
  }
}

onMounted(async () => {
  const skipUpdate = sessionStorage.getItem('skip_update');
  if (skipUpdate) {
    emit('skip');
    return;
  }

  if (get(headless))
    await check();
});
</script>

<template>
  <div>
    <AssetUpdateSetting
      v-if="!headless"
      :loading="checking || applying"
      :skipped="skipped"
      @check="check()"
    />
    <template v-else-if="headless">
      <AssetUpdateStatus
        v-if="status"
        :status="status"
        :remote-version="changes.upToVersion"
      />
      <AssetUpdateInlineConfirm
        v-if="inlineConfirm"
        class="max-w-[32rem] mx-auto"
        :remote-version="changes.upToVersion"
        @confirm="updateComplete()"
      />
    </template>
    <template v-if="showUpdateDialog">
      <RuiDialog
        v-if="!headless"
        :model-value="true"
        max-width="500"
        persistent
      >
        <AssetUpdateMessage
          :headless="headless"
          :versions="changes"
          @update:versions="changes = $event"
          @confirm="updateAssets()"
          @dismiss="skip($event)"
        />
      </RuiDialog>
      <AssetUpdateMessage
        v-else
        class="max-w-[32rem] mx-auto"
        :headless="headless"
        :versions="changes"
        @update:versions="changes = $event"
        @confirm="updateAssets()"
        @dismiss="skip($event)"
      />
    </template>

    <AssetConflictDialog
      v-if="showConflictDialog"
      v-model="showConflictDialog"
      :conflicts="conflicts"
      @cancel="skip(false)"
      @resolve="updateAssets($event)"
    />
  </div>
</template>

<style scoped lang="scss">
.asset-update {
  &__partial {
    margin-top: 6px !important;
    height: 60px;
  }
}
</style>
