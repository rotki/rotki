<script setup lang="ts">
import { Severity } from '@rotki/common/lib/messages';
import { DialogType } from '@/types/dialogs';
import { TaskType } from '@/types/task-type';

withDefaults(
  defineProps<{
    dropdown?: boolean;
  }>(),
  { dropdown: false },
);

type ResetType = 'soft' | 'hard';

const { notify } = useNotificationsStore();
const { connect, setConnected } = useMainStore();
const { logout } = useSessionStore();
const { restoreAssetsDatabase } = useAssets();

const { restartBackend } = useBackendManagement();

const { t } = useI18n();

const { isTaskRunning } = useTaskStore();
const loading = isTaskRunning(TaskType.RESET_ASSET);

async function restoreAssets(resetType: ResetType) {
  if (get(loading))
    return;

  const result = await restoreAssetsDatabase(resetType);

  if (result.success) {
    showDoneConfirmation();
  }
  else {
    const { message } = result;
    const title = t('asset_update.restore.title').toString();
    if (message.includes('There are assets that can not'))
      showDoubleConfirmation(resetType);

    notify({
      title,
      message,
      severity: Severity.ERROR,
      display: true,
    });
  }
}

async function updateComplete() {
  await logout();
  setConnected(false);
  await restartBackend();
  await connect();
}

const { show } = useConfirmStore();

function showRestoreConfirmation(type: ResetType) {
  show(
    {
      title: t('asset_update.restore.delete_confirmation.title'),
      message:
        type === 'soft'
          ? t('asset_update.restore.delete_confirmation.soft_reset_message')
          : t('asset_update.restore.delete_confirmation.hard_reset_message'),
    },
    () => restoreAssets(type),
  );
}

function showDoubleConfirmation(type: ResetType) {
  show(
    {
      title: t('asset_update.restore.hard_restore_confirmation.title'),
      message: t('asset_update.restore.hard_restore_confirmation.message'),
    },
    () => restoreAssets(type),
  );
}

function showDoneConfirmation() {
  show(
    {
      title: t('asset_update.restore.success.title'),
      message: t('asset_update.restore.success.description'),
      primaryAction: t('common.actions.ok'),
      singleAction: true,
      type: DialogType.SUCCESS,
    },
    updateComplete,
  );
}
</script>

<template>
  <RuiMenu
    v-if="dropdown"
    :popper="{ placement: 'left-start' }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        id="reset-asset-activator"
        variant="list"
        :disabled="loading"
        v-bind="attrs"
      >
        <template #prepend>
          <RuiIcon name="restart-line" />
        </template>
        {{ t('asset_update.restore.title') }}
        <template #append>
          <RuiIcon name="arrow-down-s-line" />
        </template>
      </RuiButton>
    </template>
    <div class="py-2">
      <ListItem
        :title="t('asset_update.restore.soft_reset')"
        :subtitle="t('asset_update.restore.soft_reset_hint')"
        @click="showRestoreConfirmation('soft')"
      />
      <ListItem
        :title="t('asset_update.restore.hard_reset')"
        :subtitle="t('asset_update.restore.hard_reset_hint')"
        @click="showRestoreConfirmation('hard')"
      />
    </div>
  </RuiMenu>
  <div
    v-else
    class="flex flex-row gap-2"
  >
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          variant="outlined"
          color="primary"
          :loading="loading"
          @click="showRestoreConfirmation('soft')"
        >
          {{ t('asset_update.restore.soft_reset') }}
        </RuiButton>
      </template>
      {{ t('asset_update.restore.soft_reset_hint') }}
    </RuiTooltip>
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          color="primary"
          :loading="loading"
          @click="showRestoreConfirmation('hard')"
        >
          {{ t('asset_update.restore.hard_reset') }}
        </RuiButton>
      </template>
      {{ t('asset_update.restore.hard_reset_hint') }}
    </RuiTooltip>
  </div>
</template>
