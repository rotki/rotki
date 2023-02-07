<script setup lang="ts">
const { t } = useI18n();

const { queryingLength, length, isAllFinished } = toRefs(
  useTxQueryStatusStore()
);
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
