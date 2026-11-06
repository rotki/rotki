<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { MergeSuggestion } from '@/modules/assets/admin/solana-token-migration/use-solana-token-migration-dialog';
import { SolanaTokenKind } from '@rotki/common';
import { msg } from '@/message-key';
import AssetManagerMoreTitle from '@/modules/assets/admin/AssetManagerMoreTitle.vue';
import MergeDialog from '@/modules/assets/admin/MergeDialog.vue';
import SolanaTokenMigrationDialog from '@/modules/assets/admin/solana-token-migration/SolanaTokenMigrationDialog.vue';
import { useSolanaTokenMigrationStore } from '@/modules/assets/admin/solana-token-migration/use-solana-token-migration-store';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.manage_assets_sub.solana_token_migration'), icon: 'lu-coins', parent: '/asset-manager/' },
  },
});

const { t } = useI18n({ useScope: 'global' });

const solanaTokenMigrationStore = useSolanaTokenMigrationStore();
const { identifiers } = storeToRefs(solanaTokenMigrationStore);
const { removeIdentifier } = solanaTokenMigrationStore;

const migrationData = ref<{
  address: string;
  decimals: number | null;
  tokenKind: string;
} | undefined>();

const oldAsset = ref<string>();
const mergeTool = ref<boolean>(false);
const mergeSourceIdentifier = ref<string>();
const mergeTargetIdentifier = ref<string>();

const rows = computed(() => get(identifiers).map((identifier, index) => ({
  id: index,
  identifier,
})));

const cols = computed<DataTableColumn<{ id: number; identifier: string }>[]>(() => [
  {
    class: 'w-full',
    key: 'identifier',
    label: t('common.asset'),
    sortable: true,
  },
  {
    align: 'end',
    cellClass: 'w-px',
    key: 'actions',
    label: t('common.actions_text'),
  },
]);

function openMigrationDialog(identifier: string) {
  set(migrationData, {
    address: '',
    decimals: null,
    tokenKind: SolanaTokenKind.SPL_TOKEN,
  });
  set(oldAsset, identifier);
}

function openMergeDialog(identifier: string) {
  set(mergeSourceIdentifier, identifier);
  set(mergeTool, true);
}

/**
 * Opens the merge tool with both assets already chosen.
 *
 * @remarks
 * Runs only once the user has accepted the suggestion in the migration dialog, so the merge dialog
 * opens on the pair the suggestion named rather than empty.
 */
function openMergePrefilledWith({ sourceAsset, targetAsset }: MergeSuggestion): void {
  set(mergeSourceIdentifier, sourceAsset);
  set(mergeTargetIdentifier, targetAsset);
  set(mergeTool, true);
}

function handleMergeCompleted({ sourceIdentifier }: { sourceIdentifier: string; targetIdentifier: string }): void {
  removeIdentifier(sourceIdentifier);

  set(mergeSourceIdentifier, undefined);
  set(mergeTargetIdentifier, undefined);
}
</script>

<template>
  <TablePageLayout child>
    <template #title>
      <AssetManagerMoreTitle />
    </template>
    <TableFrame>
      <RuiDataTable
        dense
        :rows="rows"
        :cols="cols"
        :pagination="{
          limit: 10,
          page: 1,
          total: rows.length,
        }"
        row-attr="id"
      >
        <template #item.identifier="{ row }">
          <AssetDetails
            :asset="row.identifier"
            :display="{ dense: true }"
          />
        </template>
        <template #item.actions="{ row }">
          <div class="flex items-center justify-end gap-2">
            <RuiButton
              size="sm"
              variant="text"
              color="primary"
              data-testid="solana-token-merge"
              @click="openMergeDialog(row.identifier)"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-combine"
                  size="16"
                />
              </template>
              {{ t('asset_management.merge_assets') }}
            </RuiButton>
            <RuiButton
              size="sm"
              variant="outlined"
              color="primary"
              data-testid="solana-token-migrate"
              @click="openMigrationDialog(row.identifier)"
            >
              {{ t('asset_management.solana_token_migration.migrate_button') }}
              <template #append>
                <RuiIcon
                  name="lu-arrow-right"
                  size="16"
                />
              </template>
            </RuiButton>
          </div>
        </template>
      </RuiDataTable>
    </TableFrame>

    <SolanaTokenMigrationDialog
      v-model="migrationData"
      v-model:old-asset="oldAsset"
      @suggest-merge="openMergePrefilledWith($event)"
    />

    <MergeDialog
      v-model="mergeTool"
      :source-identifier="mergeSourceIdentifier"
      :target-identifier="mergeTargetIdentifier"
      @merged="handleMergeCompleted($event)"
    />
  </TablePageLayout>
</template>
