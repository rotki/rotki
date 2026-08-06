<script setup lang="ts">
import type { AssetUpdateConflictResult, AssetVersionUpdate, ConflictResolution } from '@/modules/assets/types';
import { useAssets } from '@/modules/assets/use-assets';
import { useRestartingStatus } from '@/modules/auth/use-restarting-status';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import AssetConflictDialog from '@/modules/shell/app/AssetConflictDialog.vue';
import AssetUpdateInlineConfirm from '@/modules/shell/app/AssetUpdateInlineConfirm.vue';
import AssetUpdateMessage from '@/modules/shell/app/AssetUpdateMessage.vue';
import AssetUpdateSetting from '@/modules/shell/app/AssetUpdateSetting.vue';
import AssetUpdateStatus from '@/modules/shell/app/AssetUpdateStatus.vue';
import { useBackendReload } from '@/modules/shell/app/use-backend-reload';

const { headless = false } = defineProps<{ headless?: boolean }>();

const emit = defineEmits<{
  skip: [];
}>();
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

const { applyUpdates, checkForUpdate } = useAssets();
const { reload } = useBackendReload();

const { t } = useI18n({ useScope: 'global' });
const { setMessage } = useMessageStore();

async function check() {
  set(checking, true);
  const checkResult = await checkForUpdate();
  set(checking, false);
  const skippedVersion = get(skipped);
  const versions = checkResult.versions;
  if (headless && skippedVersion && skippedVersion === versions?.remote) {
    set(checking, false);
    emit('skip');
    return;
  }

  set(showUpdateDialog, checkResult.updateAvailable);

  if (!checkResult.updateAvailable) {
    if (headless) {
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
  try {
    await reload();
  }
  finally {
    // Always cleared: a reload that reports a failure still ends this attempt, and
    // leaving the flag set would block every later one.
    set(restarting, false);
  }
}

const { show } = useConfirmStore();

function showDoneConfirmation() {
  if (headless) {
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

  if (headless)
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
        model-value
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
