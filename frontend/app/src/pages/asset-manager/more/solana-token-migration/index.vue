<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import MergeDialog from '@/components/asset-manager/MergeDialog.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useSolanaTokenMigrationStore } from '@/modules/asset-manager/solana-token-migration/solana-token-migration-store';
import SolanaTokenMigrationDialog from '@/modules/asset-manager/solana-token-migration/SolanaTokenMigrationDialog.vue';
import { useConfirmStore } from '@/store/confirm';
import { SolanaTokenKind } from '@rotki/common';

definePage({
  name: 'asset-manager-solana-token-migration',
});

const { t } = useI18n({ useScope: 'global' });

const solanaTokenMigrationStore = useSolanaTokenMigrationStore();
const { identifiers } = storeToRefs(solanaTokenMigrationStore);
const { removeIdentifier } = solanaTokenMigrationStore;
const { show } = useConfirmStore();

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
    key: 'actions',
    label: t('common.actions_text'),
    sortable: true,
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

function handleMergeSuggestion({ sourceAsset, targetAsset }: { sourceAsset: string; targetAsset: string }) {
  show(
    {
      message: t('asset_management.solana_token_migration.merge_suggestion.message', {
        sourceAsset,
        targetAsset,
      }),
      title: t('asset_management.solana_token_migration.merge_suggestion.title'),
    },
    () => {
      // User confirmed - open merge dialog with prefilled values
      set(mergeSourceIdentifier, sourceAsset);
      set(mergeTargetIdentifier, targetAsset);
      set(mergeTool, true);
    },
  );
}

function handleMergeCompleted({ sourceIdentifier }: { sourceIdentifier: string; targetIdentifier: string }) {
  // Remove the source identifier from the migration list since it was successfully merged
  removeIdentifier(sourceIdentifier);

  // Clear the merge dialog state
  set(mergeSourceIdentifier, undefined);
  set(mergeTargetIdentifier, undefined);
}
</script>

<template>
  <TablePageLayout
    child
    hide-header
    class="lg:!-mt-5"
  >
    <RuiCard>
      <RuiDataTable
        dense
        :rows="rows"
        :cols="cols"
        :pagination="{
          limit: 10,
          page: 1,
          total: rows.length,
        }"
        :pagination-modifiers="{ external: false }"
        row-attr="id"
        outlined
      >
        <template #item.identifier="{ row }">
          <AssetDetails
            :asset="row.identifier"
            dense
          />
        </template>
        <template #item.actions="{ row }">
          <div class="flex gap-2">
            <RuiButton
              color="primary"
              variant="text"
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
            <RuiDivider vertical />
            <RuiButton
              color="primary"
              variant="text"
              @click="openMergeDialog(row.identifier)"
            >
              {{ t('asset_management.merge_assets') }}
              <template #append>
                <RuiIcon
                  name="lu-combine"
                  size="16"
                />
              </template>
            </RuiButton>
          </div>
        </template>
      </RuiDataTable>
    </RuiCard>

    <SolanaTokenMigrationDialog
      v-model="migrationData"
      v-model:old-asset="oldAsset"
      @suggest-merge="handleMergeSuggestion($event)"
    />

    <MergeDialog
      v-model="mergeTool"
      :source-identifier="mergeSourceIdentifier"
      :target-identifier="mergeTargetIdentifier"
      @merged="handleMergeCompleted($event)"
    />
  </TablePageLayout>
</template>
