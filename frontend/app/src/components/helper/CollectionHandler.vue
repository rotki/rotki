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
<script setup lang="ts">
import { type PropType } from 'vue';
import { type Collection } from '@/types/collection';
import { getCollectionData, setupEntryLimit } from '@/utils/collection';

const props = defineProps({
  collection: {
    required: true,
    type: Object as PropType<Collection<any>>
  }
});

const { collection } = toRefs(props);

const { data, limit, found, total, totalUsdValue } =
  getCollectionData(collection);

const { showUpgradeRow, itemLength } = setupEntryLimit(limit, found, total);
</script>
