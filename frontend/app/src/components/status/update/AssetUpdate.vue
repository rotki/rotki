<template>
  <fragment>
    <card v-if="!auto" class="mt-8">
      <template #title>{{ tc('asset_update.manual.title') }}</template>
      <template #subtitle>{{ tc('asset_update.manual.subtitle') }}</template>
      <div v-if="skipped && skipped !== 'undefined'" class="text-body-1">
        <i18n path="asset_update.manual.skipped">
          <template #skipped>
            <badge-display class="ml-2">{{ skipped }}</badge-display>
          </template>
        </i18n>
      </div>
      <template #buttons>
        <v-btn depressed color="primary" :loading="checking" @click="check">
          {{ tc('asset_update.manual.check') }}
        </v-btn>
      </template>
    </card>
    <v-dialog
      v-if="showUpdateDialog"
      v-model="showUpdateDialog"
      max-width="500"
      persistent
    >
      <card>
        <template #title>{{ tc('asset_update.title') }}</template>
        <i18n class="text-body-1" tag="div" path="asset_update.description">
          <template #remote>
            <span class="font-weight-medium">{{ remoteVersion }}</span>
          </template>
          <template #local>
            <span class="font-weight-medium">{{ localVersion }}</span>
          </template>
        </i18n>
        <div class="text-body-1 mt-4">
          {{ tc('asset_update.total_changes', 0, { changes }) }}
        </div>

        <div v-if="multiple" class="font-weight-medium text-body-1 mt-4">
          {{ tc('asset_update.advanced') }}
        </div>
        <v-row v-if="multiple">
          <v-col>
            <v-checkbox
              v-model="partial"
              class="asset-update__partial"
              dense
              :label="tc('asset_update.partially_update')"
            />
          </v-col>
          <v-col cols="6">
            <v-text-field
              v-if="partial"
              v-model="upToVersion"
              outlined
              type="number"
              dense
              :min="localVersion"
              :max="remoteVersion"
              :label="tc('asset_update.up_to_version')"
              @change="onChange"
            />
          </v-col>
        </v-row>
        <template #options>
          <v-checkbox
            v-if="auto"
            v-model="skipUpdate"
            dense
            :label="tc('asset_update.skip_notification')"
          />
        </template>
        <template #buttons>
          <v-row justify="end" no-gutters>
            <v-col cols="auto">
              <v-btn text @click="skip">
                {{ tc('common.actions.skip') }}
              </v-btn>
            </v-col>
            <v-col cols="auto">
              <v-btn text color="primary" @click="updateAssets()">
                {{ tc('common.actions.update') }}
              </v-btn>
            </v-col>
          </v-row>
        </template>
      </card>
    </v-dialog>
    <conflict-dialog
      v-if="showConflictDialog"
      v-model="showConflictDialog"
      :conflicts="conflicts"
      @cancel="showConflictDialog = false"
      @resolve="updateAssets($event)"
    />
    <confirm-dialog
      v-if="done"
      single-action
      display
      :title="tc('asset_update.success.title')"
      :primary-action="tc('asset_update.success.ok')"
      :message="
        tc('asset_update.success.description', 0, {
          remoteVersion
        })
      "
      @confirm="updateComplete()"
    />
  </fragment>
</template>

<script setup lang="ts">
import { Ref } from 'vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import Fragment from '@/components/helper/Fragment';
import ConflictDialog from '@/components/status/update/ConflictDialog.vue';
import { useBackendManagement } from '@/composables/backend';
import { ConflictResolution } from '@/services/assets/types';
import { useAssets } from '@/store/assets';
import { useMainStore } from '@/store/main';
import { useMessageStore } from '@/store/message';
import { useSessionStore } from '@/store/session';
import { AssetUpdateConflictResult } from '@/types/assets';

const props = defineProps({
  auto: { required: false, default: false, type: Boolean }
});

const { auto } = toRefs(props);
const showUpdateDialog: Ref<boolean> = ref(false);
const showConflictDialog: Ref<boolean> = ref(false);
const skipUpdate: Ref<boolean> = ref(false);
const localVersion: Ref<number> = ref(0);
const remoteVersion: Ref<number> = ref(0);
const changes: Ref<number> = ref(0);
const upToVersion: Ref<number> = ref(0);
const partial: Ref<boolean> = ref(false);

const conflicts: Ref<AssetUpdateConflictResult[]> = ref([]);
const done: Ref<boolean> = ref(false);

const skipped = useLocalStorage('rotki_skip_asset_db_version', undefined);

const { logout } = useSessionStore();
const { checkForUpdate, applyUpdates } = useAssets();
const { connect, setConnected } = useMainStore();
const { restartBackend } = useBackendManagement();

const { tc } = useI18n();

const multiple = computed(() => {
  return get(remoteVersion) - get(localVersion) > 1;
});

const checking: Ref<boolean> = ref(false);
const { setMessage } = useMessageStore();

const check = async () => {
  set(checking, true);
  const checkResult = await checkForUpdate();
  set(checking, false);
  const skippedVersion = get(skipped);
  const versions = checkResult.versions;
  if (get(auto) && skippedVersion && skippedVersion === versions?.remote) {
    set(checking, false);
    return;
  }

  set(showUpdateDialog, checkResult.updateAvailable);

  if (!get(auto) && !checkResult.updateAvailable) {
    setMessage({
      description: tc('asset_update.up_to_date'),
      success: true
    });
  }

  if (versions) {
    set(localVersion, versions.local);
    set(remoteVersion, versions.remote);
    set(changes, versions.newChanges);
    set(upToVersion, versions.remote);
  }
};

const skip = () => {
  set(showUpdateDialog, false);
  set(showConflictDialog, false);
  if (get(skipUpdate)) {
    set(skipped, get(remoteVersion));
  }
};

const onChange = (value: string) => {
  const number = parseInt(value);
  const local = get(localVersion);
  if (isNaN(number)) {
    set(upToVersion, local + 1);
  } else {
    if (number < local) {
      set(upToVersion, local + 1);
    } else if (number > get(remoteVersion)) {
      set(upToVersion, get(remoteVersion));
    } else {
      set(upToVersion, number);
    }
  }
};

const updateAssets = async (resolution?: ConflictResolution) => {
  set(showUpdateDialog, false);
  set(showConflictDialog, false);
  const version = get(multiple) ? get(upToVersion) : get(remoteVersion);
  const updateResult = await applyUpdates({ version, resolution });
  if (updateResult.done) {
    set(skipped, undefined);
    set(done, true);
  } else if (updateResult.conflicts) {
    set(conflicts, updateResult.conflicts);
    set(showConflictDialog, true);
  }
};

const updateComplete = async () => {
  await logout();
  setConnected(false);
  await restartBackend();
  await connect();
};

onMounted(async () => {
  const skipUpdate = sessionStorage.getItem('skip_update');
  if (skipUpdate) {
    return;
  }

  if (get(auto)) {
    await check();
  }
});
</script>

<style scoped lang="scss">
.asset-update {
  &__partial {
    margin-top: 6px !important;
    height: 60px;
  }
}
</style>
