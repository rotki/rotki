<template>
  <table-expand-container visible :colspan="span">
    <template #title>
      {{ $t('deposits_withdrawals.details.title') }}
    </template>
    <movement-links v-if="item.address || item.transactionId" :item="item" />
    <div v-else class="font-weight-medium pa-4" :class="$style.empty">
      {{ $t('deposits_withdrawals.details.no_details') }}
    </div>
  </table-expand-container>
</template>
<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import MovementLinks from '@/components/history/MovementLinks.vue';
import { AssetMovementEntry } from '@/store/history/types';

export default defineComponent({
  name: 'DepositWithdrawalDetails',
  components: { MovementLinks, TableExpandContainer },
  props: {
    span: {
      type: Number,
      required: true
    },
    item: {
      required: true,
      type: Object as PropType<AssetMovementEntry>
    }
  }
});
</script>
<style module lang="scss">
.empty {
  height: 100px;
}

::v-deep {
  th {
    &:nth-child(2) {
      span {
        padding-left: 16px;
      }
    }
  }
}
</style>
