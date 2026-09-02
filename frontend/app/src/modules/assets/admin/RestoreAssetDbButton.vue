<script setup lang="ts">
import { Severity } from '@rotki/common';
import { useAssets } from '@/modules/assets/use-assets';
import { DialogType } from '@/modules/core/common/dialogs';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { useBackendReload } from '@/modules/shell/app/use-backend-reload';
import ListItem from '@/modules/shell/components/ListItem.vue';
import { ActivityPart } from '@/modules/task-center/core/types';
import { ActivityKind, useTaskCenter } from '@/modules/task-center/use-task-center';

const { dropdown = false } = defineProps<{
  dropdown?: boolean;
}>();

type ResetType = 'soft' | 'hard';

const { notify } = useNotificationDispatcher();
const { restoreAssetsDatabase } = useAssets();
const { reload } = useBackendReload();

const { t } = useI18n({ useScope: 'global' });

const { useIsActive } = useTaskCenter();
const loading = useIsActive(ActivityKind.ASSETS, ActivityPart.RESET);

async function restoreAssets(resetType: ResetType) {
  if (get(loading))
    return;

  const result = await restoreAssetsDatabase(resetType);

  if (result.success) {
    showDoneConfirmation();
  }
  else {
    const { message } = result;
    const title = t('asset_update.restore.title');
    if (message.includes('There are assets that can not'))
      showDoubleConfirmation(resetType);

    notify({
      display: true,
      message,
      severity: Severity.ERROR,
      title,
    });
  }
}

async function updateComplete() {
  await reload();
}

const { show } = useConfirmStore();

function showRestoreConfirmation(type: ResetType) {
  show(
    {
      message:
        type === 'soft'
          ? t('asset_update.restore.delete_confirmation.soft_reset_message')
          : t('asset_update.restore.delete_confirmation.hard_reset_message'),
      title: t('asset_update.restore.delete_confirmation.title'),
    },
    () => restoreAssets(type),
  );
}

function showDoubleConfirmation(type: ResetType) {
  show(
    {
      message: t('asset_update.restore.hard_restore_confirmation.message'),
      title: t('asset_update.restore.hard_restore_confirmation.title'),
    },
    () => restoreAssets(type),
  );
}

function showDoneConfirmation() {
  show(
    {
      message: t('asset_update.restore.success.description'),
      primaryAction: t('common.actions.ok'),
      singleAction: true,
      title: t('asset_update.restore.success.title'),
      type: DialogType.SUCCESS,
    },
    updateComplete,
  );
}
</script>

<template>
  <RuiMenu
    v-if="dropdown"
    :options="{ placement: 'left-start' }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="list"
        :disabled="loading"
        v-bind="{ ...attrs, id: 'reset-asset-activator' }"
      >
        <template #prepend>
          <RuiIcon name="lu-rotate-ccw" />
        </template>
        {{ t('asset_update.restore.title') }}
        <template #append>
          <RuiIcon name="lu-chevron-down" />
        </template>
      </RuiButton>
    </template>
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
  </RuiMenu>
  <div
    v-else
    class="flex flex-col gap-4"
  >
    <RuiCard>
      <div class="flex justify-between items-center gap-2">
        {{ t('asset_update.restore.soft_reset_hint') }}
        <RuiButton
          variant="outlined"
          color="error"
          :loading="loading"
          @click="showRestoreConfirmation('soft')"
        >
          {{ t('asset_update.restore.soft_reset') }}
        </RuiButton>
      </div>
    </RuiCard>
    <RuiCard>
      <div class="flex justify-between items-center gap-2">
        {{ t('asset_update.restore.hard_reset_hint') }}
        <RuiButton
          color="error"
          :loading="loading"
          @click="showRestoreConfirmation('hard')"
        >
          {{ t('asset_update.restore.hard_reset') }}
        </RuiButton>
      </div>
    </RuiCard>
  </div>
</template>
