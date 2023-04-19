<script setup lang="ts">
import { type Collection } from '@/types/collection';

const props = defineProps<{
  collection: Collection<any>;
}>();

const emit = defineEmits<{
  (e: 'set-page', page: number): void;
}>();

const setPage = (page: number) => {
  emit('set-page', page);
};

const { collection } = toRefs(props);

const { data, limit, found, total, totalUsdValue } =
  getCollectionData(collection);

const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());
watch([data, found, itemsPerPage], ([data, found, itemsPerPage]) => {
  if (data.length === 0 && found > 0) {
    const lastPage = Math.ceil(found / itemsPerPage);
    setPage(lastPage);
  }
});

const { showUpgradeRow, itemLength } = setupEntryLimit(limit, found, total);
</script>
<template>
  <div>
    <slot
      :data="data"
      :limit="limit"
      :found="found"
      :total="total"
      :total-usd-value="totalUsdValue"
      :item-length="itemLength"
      :show-upgrade-row="showUpgradeRow"
    />
  </div>
</template>
