<script setup lang="ts" generic="T extends object">
import type { Collection } from '@/types/collection';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { getCollectionData, setupEntryLimit } from '@/utils/collection';

const props = defineProps<{
  collection: Collection<T>;
}>();

const emit = defineEmits<{
  (e: 'set-page', page: number): void;
}>();

function setPage(page: number) {
  emit('set-page', page);
}

const { collection } = toRefs(props);

const { data, entriesFoundTotal, found, limit, total, totalUsdValue } = getCollectionData(collection);

const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());
watch([data, found, itemsPerPage], ([data, found, itemsPerPage]) => {
  if (data.length === 0 && found > 0) {
    const lastPage = Math.ceil(found / itemsPerPage);
    setPage(lastPage);
  }
});

const { itemLength, showUpgradeRow } = setupEntryLimit(limit, found, total, entriesFoundTotal);
</script>

<template>
  <div>
    <slot
      :data="data"
      :limit="limit"
      :found="found"
      :total="total"
      :entries-found-total="entriesFoundTotal"
      :total-usd-value="totalUsdValue"
      :item-length="itemLength"
      :show-upgrade-row="showUpgradeRow"
    />
  </div>
</template>
