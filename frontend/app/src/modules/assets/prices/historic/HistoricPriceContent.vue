<script setup lang="ts">
import type { HistoricalPrice, HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import { RuiButton, RuiIcon, RuiTooltip } from '@rotki/ui-library';
import { get, set } from '@vueuse/shared';
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import HistoricPriceFormDialog from '@/modules/assets/prices/historic/HistoricPriceFormDialog.vue';
import HistoricPriceTable from '@/modules/assets/prices/historic/HistoricPriceTable.vue';
import { HistoricPriceFilterKeys, useHistoricPriceFields } from '@/modules/assets/prices/use-historic-price-fields';
import { useHistoricPrices } from '@/modules/assets/prices/use-historic-price-manager';
import { type PriceAddLink, usePriceAddLink } from '@/modules/assets/prices/use-price-add-link';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });

const emptyPrice: () => HistoricalPriceFormPayload = () => ({
  fromAsset: '',
  price: '',
  sourceType: PriceOracle.MANUAL,
  timestamp: Math.floor(Date.now() / 1000),
  toAsset: '',
});

const modelValue = ref<HistoricalPriceFormPayload>();
const editMode = ref<boolean>(false);

const fields = useHistoricPriceFields();
const pillLabels = usePillBarLabels();

/**
 * The bar owns the bag, and the table reads the pair out of it.
 *
 * Deliberately not a writable computed over a `{ fromAsset, toAsset }` ref: a pill exists before it
 * has a value, and a bridge that rebuilds the object from the two keys drops that pending state, so
 * the pill vanished the moment it was added.
 */
const matches = ref<MatchedKeywordWithBehaviour<string>>({});

const filter = computed<{ fromAsset?: string; toAsset?: string }>(() => {
  const bag = get(matches);
  const picked = (key: string): string | undefined => {
    const value = bag[key];
    return typeof value === 'string' && value !== '' ? value : undefined;
  };

  return {
    fromAsset: picked(HistoricPriceFilterKeys.FROM_ASSET),
    toAsset: picked(HistoricPriceFilterKeys.TO_ASSET),
  };
});

const { deletePrice, emptyState, items, loading, refresh } = useHistoricPrices(filter);

/**
 * Opens the add dialog, seeded from the table filter, or from the `?add=` link when it names the
 * asset (`fromAsset`) and the time (`timestamp`, in seconds) of a price the backend found missing.
 */
function add(link?: PriceAddLink) {
  const price = emptyPrice();
  set(modelValue, {
    ...price,
    fromAsset: link?.fromAsset || (get(filter).fromAsset ?? ''),
    timestamp: link?.timestamp || price.timestamp,
    toAsset: get(filter).toAsset ?? '',
  });
  set(editMode, false);
}

function edit(item: HistoricalPrice) {
  set(modelValue, {
    ...item,
    price: item.price.toFixed() ?? '',
    sourceType: PriceOracle.MANUAL,
  });
  set(editMode, true);
}

const { consumeAddQuery } = usePriceAddLink(add);

onMounted(async () => {
  await consumeAddQuery();
});
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.manage_prices'), t('navigation_menu.manage_prices_sub.historic_prices')]"
  >
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="loading"
            @click="refresh()"
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
        data-testid="historic-price-add"
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
          {{ t('price_management.historic.hint') }}
        </HintMenuIcon>
        <PillFilterBar
          v-model:matches="matches"
          class="flex-1 min-w-48 md:min-w-96"
          :fields="fields"
          :labels="pillLabels"
        />
      </template>
      <HistoricPriceTable
        :rows="items"
        :loading="loading"
        :disabled="loading"
        :empty-state="emptyState"
        @delete="deletePrice($event)"
        @edit="edit($event)"
      />
    </TableFrame>

    <HistoricPriceFormDialog
      v-model="modelValue"
      :edit-mode="editMode"
      @refresh="refresh({ modified: true })"
    />
  </TablePageLayout>
</template>
