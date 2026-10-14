<script setup lang="ts">
import SnapshotImportDialog from '@/modules/dashboard/SnapshotImportDialog.vue';
import { useSnapshotActions } from '@/modules/dashboard/snapshots/composables/use-snapshot-actions';
import { usePremium } from '@/modules/premium/use-premium';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';

const visible = ref<boolean>(false);
const importSnapshotDialog = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });
const premium = usePremium();
const { lastBalanceSave } = storeToRefs(useSessionMetadataStore());
const { forceSave, forceSaving, importing, importSnapshot, modelBalanceFile, modelLocationFile } = useSnapshotActions();

async function forceSaveAndClose(): Promise<void> {
  set(visible, false);
  await forceSave();
}
</script>

<template>
  <RuiMenu
    id="snapshot-action-menu"
    v-model="visible"
    :options="{ placement: 'bottom-end' }"
    :persistent="importSnapshotDialog"
  >
    <template #activator="{ attrs }">
      <MenuTooltipButton
        :tooltip="t('snapshot_action_button.menu_tooltip', premium ? 2 : 1)"
        variant="default"
        size="sm"
        custom-color
        v-bind="attrs"
        class="p-2!"
        data-testid="snapshot-action"
      >
        <RuiIcon name="lu-git-commit-vertical" />
      </MenuTooltipButton>
    </template>
    <div class="p-4 md:w-64 w-full flex flex-col gap-4">
      <div class="flex flex-col gap-0.5">
        <div class="font-medium">
          {{ t('snapshot_action_button.snapshot_title') }}
        </div>
        <div
          class="text-sm text-rui-text-secondary"
          data-testid="snapshot-last-save"
        >
          <TimeAgoDisplay
            v-if="lastBalanceSave"
            :timestamp="lastBalanceSave"
          />
          <span v-else>{{ t('common.never') }}</span>
        </div>
      </div>

      <RuiDivider />

      <div class="flex flex-col gap-2">
        <div class="flex items-center gap-4">
          <RuiButton
            color="primary"
            variant="outlined"
            :loading="forceSaving"
            @click="forceSaveAndClose()"
          >
            <template #prepend>
              <RuiIcon name="lu-save" />
            </template>
            {{ t('snapshot_action_button.force_save') }}
          </RuiButton>

          <RuiTooltip
            :open-delay="400"
            :class-names="{ tooltip: 'max-w-64' }"
          >
            <template #activator>
              <RuiIcon
                name="lu-info"
                size="18"
                color="primary"
              />
            </template>
            {{ t('snapshot_action_button.snapshot_tooltip') }}
          </RuiTooltip>
        </div>

        <RuiTooltip
          :open-delay="400"
          :class-names="{ tooltip: 'max-w-64' }"
        >
          <template #activator>
            <SettingSwitch
              setting="ignoreSnapshotError"
              control="checkbox"
              :label="t('snapshot_action_button.ignore_errors_label')"
              hide-details
            />
          </template>
          {{ t('snapshot_action_button.ignore_errors_tooltip') }}
        </RuiTooltip>
      </div>

      <RuiDivider />

      <div>
        <div class="font-medium pb-2">
          {{ t('snapshot_import_dialog.title') }}
        </div>
        <SnapshotImportDialog
          v-model="importSnapshotDialog"
          v-model:balance-file="modelBalanceFile"
          v-model:location-file="modelLocationFile"
          :loading="importing"
          @import="importSnapshot()"
        />
      </div>
    </div>
  </RuiMenu>
</template>
