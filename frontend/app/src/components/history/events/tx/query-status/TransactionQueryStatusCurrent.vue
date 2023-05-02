<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';

const props = withDefaults(
  defineProps<{
    onlyChains?: Blockchain[];
  }>(),
  {
    onlyChains: () => []
  }
);

const { onlyChains } = toRefs(props);

const { t } = useI18n();

const { isAllFinished } = toRefs(useTxQueryStatusStore());
const { queryingLength, length } = useTransactionQueryStatus(onlyChains);
</script>

<template>
  <div>
    <div v-if="isAllFinished">
      {{ t('transactions.query_status.done_group', { length }) }}
    </div>
    <div v-else>
      {{
        t('transactions.query_status.group', {
          length: queryingLength
        })
      }}
    </div>
  </div>
</template>
