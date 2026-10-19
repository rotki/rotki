<script setup lang="ts">
import TableSelectionAction from '@/modules/core/table/TableSelectionAction.vue';
import TableSelectionBar from '@/modules/core/table/TableSelectionBar.vue';
import DatabaseBackups from '@/modules/settings/data-security/backups/DatabaseBackups.vue';
import { useDatabaseBackups } from '@/modules/settings/data-security/backups/use-database-backups';
import SettingCategoryHeader from '@/modules/settings/SettingCategoryHeader.vue';

const { t } = useI18n({ useScope: 'global' });

const selectionMode = shallowRef<boolean>(false);

const {
  backup,
  backups,
  directory,
  loadInfo,
  loading,
  modelSelected,
  remove,
  saving,
  showMassDeleteConfirmation,
} = useDatabaseBackups();

function exitSelection(): void {
  set(modelSelected, []);
  set(selectionMode, false);
}
</script>

<template>
  <div>
    <div class="pb-5 flex flex-wrap gap-4 items-center justify-between">
      <SettingCategoryHeader>
        <template #title>
          {{ t('database_settings.user_backups.title') }}
        </template>
      </SettingCategoryHeader>
      <div class="flex flex-wrap gap-2">
        <RuiTooltip
          v-if="!selectionMode"
          :options="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RuiButton
              variant="text"
              :disabled="backups.length === 0"
              data-testid="backups-select"
              @click="selectionMode = true"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-copy-check"
                  size="18"
                />
              </template>
              {{ t('common.actions.select') }}
            </RuiButton>
          </template>
          {{ t('database_settings.user_backups.enter_selection_mode') }}
        </RuiTooltip>
        <RuiButton
          variant="outlined"
          color="primary"
          :loading="loading"
          @click="loadInfo()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-refresh-ccw"
              size="16"
            />
          </template>
          {{ t('common.refresh') }}
        </RuiButton>
        <RuiButton
          color="primary"
          :disabled="saving"
          :loading="saving"
          @click="backup()"
        >
          {{ t('database_settings.user_backups.backup_button') }}
        </RuiButton>
      </div>
    </div>
    <TableSelectionBar
      v-if="selectionMode"
      class="mb-3"
      :count="modelSelected.length"
      exitable
      @clear="modelSelected = []"
      @exit="exitSelection()"
    >
      <TableSelectionAction
        icon="lu-trash-2"
        color="error"
        :disabled="modelSelected.length === 0"
        data-testid="backups-delete-selected"
        @click="showMassDeleteConfirmation()"
      >
        {{ t('common.actions.delete') }}
      </TableSelectionAction>
    </TableSelectionBar>
    <DatabaseBackups
      v-model:selected="modelSelected"
      :selection-mode="selectionMode"
      :loading="loading"
      :items="backups"
      :directory="directory"
      @remove="remove($event)"
    />
  </div>
</template>
