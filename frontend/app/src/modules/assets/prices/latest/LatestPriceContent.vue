<script setup lang="ts">
import type { ManualPriceFormPayload, ManualPriceWithUsd } from '@/modules/assets/prices/price-types';
import { RuiButton, RuiIcon, RuiTooltip } from '@rotki/ui-library';
import { set } from '@vueuse/shared';
import { omit } from 'es-toolkit';
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import LatestPriceFormDialog from '@/modules/assets/prices/latest/LatestPriceFormDialog.vue';
import LatestPriceTable from '@/modules/assets/prices/latest/LatestPriceTable.vue';
import { useLatestPrices } from '@/modules/assets/prices/use-latest-price-manager';
import { type PriceAddLink, usePriceAddLink } from '@/modules/assets/prices/use-price-add-link';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useCommonTableProps } from '@/modules/core/table/use-common-table-props';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });

const filter = ref<string>();
const { editableItem, openDialog } = useCommonTableProps<ManualPriceFormPayload>();

const { deletePrice, emptyState, items, loading, refreshCurrentPrices, refreshing } = useLatestPrices(filter);

const prefill = ref<ManualPriceFormPayload | null>(null);

/** Opens the add dialog, seeded with the asset an `?add=` link names, if any. */
function add(link?: PriceAddLink) {
  const fromAsset = link?.fromAsset;
  set(prefill, fromAsset ? { fromAsset, price: '', toAsset: '' } : null);
  set(editableItem, null);
  set(openDialog, true);
}

function edit(item: ManualPriceWithUsd) {
  set(editableItem, omit({
    ...item,
    price: item.price.toFixed() ?? '',
  }, ['id', 'usdPrice']));
  set(openDialog, true);
}

const { consumeAddQuery } = usePriceAddLink(add);

onMounted(async () => {
  await refreshCurrentPrices();
  await consumeAddQuery();
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.manage_prices'), t('navigation_menu.manage_prices_sub.latest_prices')]">
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            color="primary"
            variant="outlined"
            :loading="loading || refreshing"
            @click="refreshCurrentPrices()"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('price_table.refresh_tooltip') }}
      </RuiTooltip>

      <RuiButton
        color="primary"
        data-testid="latest-price-add"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('price_management.dialog.add_title') }}
      </RuiButton>
    </template>

    <TableFrame>
      <template #toolbar>
        <HintMenuIcon>
          {{ t('price_management.latest.hint') }}
        </HintMenuIcon>
        <AssetSelect
          v-model="filter"
          class="w-full sm:w-80"
          dense
          :source="{ nfts: 'include' }"
          :label="t('price_management.from_asset')"
          label-placement="hidden"
          :placeholder="t('price_management.from_asset')"
          clearable
          details="hidden"
          data-testid="latest-price-filter-from"
        />
      </template>
      <LatestPriceTable
        :rows="items"
        :loading="loading || refreshing"
        :disabled="loading"
        :empty-state="emptyState"
        @delete="deletePrice($event)"
        @edit="edit($event)"
      />
    </TableFrame>

    <LatestPriceFormDialog
      v-model:open="openDialog"
      :editable-item="editableItem"
      :prefill="prefill"
      @refresh="refreshCurrentPrices()"
    />
  </TablePageLayout>
</template>
