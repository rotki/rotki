<script setup lang="ts">
import SnapshotImportDialog from '@/modules/dashboard/SnapshotImportDialog.vue';
import { useSnapshotActions } from '@/modules/dashboard/snapshots/composables/use-snapshot-actions';
import { usePremium } from '@/modules/premium/use-premium';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
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
    :popper="{ placement: 'bottom-end' }"
    :persistent="importSnapshotDialog"
  >
    <template #activator="{ attrs }">
      <MenuTooltipButton
        :tooltip="t('snapshot_action_button.menu_tooltip', premium ? 2 : 1)"
        variant="default"
        size="sm"
        custom-color
        v-bind="attrs"
        class="!p-2"
        data-testid="snapshot-action"
      >
        <RuiIcon name="lu-git-commit-vertical" />
      </MenuTooltipButton>
    </template>
    <div class="p-4 md:w-[16rem] w-full">
      <div class="font-medium">
        {{ t('snapshot_action_button.snapshot_title') }}
      </div>

      <div class="pt-0.5 text-sm text-rui-text-secondary">
        <DateDisplay
          v-if="lastBalanceSave"
          :timestamp="lastBalanceSave"
        />

        <span v-else>
          {{ t('common.never') }}
        </span>
      </div>

      <RuiDivider class="my-4" />

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
          tooltip-class="max-w-[16rem]"
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
        class="mt-2"
        :open-delay="400"
        tooltip-class="max-w-[16rem]"
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

      <RuiDivider class="mb-4" />

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
