<script setup lang="ts">
import { type Ref } from 'vue';
import Fragment from '@/components/helper/Fragment';
import {
  type AssetUpdateConflictResult,
  type AssetVersionUpdate,
  type ConflictResolution
} from '@/types/asset';

const props = withDefaults(defineProps<{ headless?: boolean }>(), {
  headless: false
});

const emit = defineEmits<{ (e: 'skip'): void; (e: 'complete'): void }>();

const { headless } = toRefs(props);
const checking: Ref<boolean> = ref(false);
const applying: Ref<boolean> = ref(false);
const inlineConfirm: Ref<boolean> = ref(false);
const showUpdateDialog: Ref<boolean> = ref(false);
const showConflictDialog: Ref<boolean> = ref(false);
const conflicts: Ref<AssetUpdateConflictResult[]> = ref([]);
const changes: Ref<AssetVersionUpdate> = ref({
  local: 0,
  remote: 0,
  changes: 0,
  upToVersion: 0
});

const skipped = useLocalStorage('rotki_skip_asset_db_version', 0);

const status = computed(() => {
  if (get(checking)) {
    return 'checking';
  }
  if (get(applying)) {
    return 'applying';
  }

  return null;
});

const { logout } = useSessionStore();
const { checkForUpdate, applyUpdates } = useAssets();
const { connect, setConnected } = useMainStore();
const { restartBackend } = useBackendManagement();

const { tc } = useI18n();
const { setMessage } = useMessageStore();

const check = async () => {
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
    } else {
      setMessage({
        description: tc('asset_update.up_to_date'),
        success: true
      });
    }
  }

  if (versions) {
    set(changes, {
      local: versions.local,
      remote: versions.remote,
      changes: versions.newChanges,
      upToVersion: versions.remote
    });
  }
};

const skip = (skipUpdate: boolean) => {
  set(showUpdateDialog, false);
  set(showConflictDialog, false);
  if (skipUpdate) {
    set(skipped, get(changes).remote);
  }
  emit('skip');
};

const updateAssets = async (resolution?: ConflictResolution) => {
  set(showUpdateDialog, false);
  set(showConflictDialog, false);
  const version = get(changes).upToVersion;
  set(applying, true);
  const updateResult = await applyUpdates({ version, resolution });
  set(applying, false);
  if (updateResult.done) {
    set(skipped, 0);
    showDoneConfirmation();
  } else if (updateResult.conflicts) {
    set(conflicts, updateResult.conflicts);
    set(showConflictDialog, true);
  }
};

const { navigateToUserLogin } = useAppNavigation();

const restarting: Ref<boolean> = ref(false);
const updateComplete = async () => {
  if (get(restarting)) {
    return;
  }

  set(restarting, true);
  await logout();
  if (!get(headless)) {
    await navigateToUserLogin();
  } else {
    emit('complete');
  }

  setConnected(false);
  await restartBackend();
  await connect();
  set(restarting, false);
};

const { show } = useConfirmStore();

const showDoneConfirmation = () => {
  if (get(headless)) {
    set(inlineConfirm, true);
  } else {
    show(
      {
        title: tc('asset_update.success.title'),
        message: tc('asset_update.success.description', 0, {
          remoteVersion: get(changes).upToVersion
        }),
        primaryAction: tc('asset_update.success.ok'),
        singleAction: true,
        type: 'success'
      },
      updateComplete
    );
  }
};

onMounted(async () => {
  const skipUpdate = sessionStorage.getItem('skip_update');
  if (skipUpdate) {
    emit('skip');
    return;
  }

  if (get(headless)) {
    await check();
  }
});
</script>

<template>
  <fragment>
    <asset-update-setting
      v-if="!headless"
      :loading="checking || applying"
      :skipped="skipped"
      @check="check()"
    />
    <div v-else-if="headless">
      <asset-update-status
        v-if="status"
        :status="status"
        :remote-version="changes.upToVersion"
      />
      <asset-update-inline-confirm
        v-if="inlineConfirm"
        :remote-version="changes.upToVersion"
        @confirm="updateComplete()"
      />
    </div>
    <div v-if="showUpdateDialog">
      <v-dialog
        v-if="!headless"
        :value="showUpdateDialog"
        max-width="500"
        persistent
      >
        <asset-update-message
          :headless="headless"
          :versions="changes"
          @update:versions="changes = $event"
          @confirm="updateAssets()"
          @dismiss="skip($event)"
        />
      </v-dialog>
      <asset-update-message
        v-else
        :headless="headless"
        :versions="changes"
        @update:versions="changes = $event"
        @confirm="updateAssets()"
        @dismiss="skip($event)"
      />
    </div>

    <conflict-dialog
      v-if="showConflictDialog"
      v-model="showConflictDialog"
      :conflicts="conflicts"
      @cancel="skip(false)"
      @resolve="updateAssets($event)"
    />
  </fragment>
</template>

<style scoped lang="scss">
.asset-update {
  &__partial {
    margin-top: 6px !important;
    height: 60px;
  }
}
</style>
