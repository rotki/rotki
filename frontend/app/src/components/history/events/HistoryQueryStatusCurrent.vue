<script setup lang="ts">
withDefaults(defineProps<{
  finished?: boolean;
}>(), {
  finished: false,
});

defineSlots<{
  finished: () => any;
  running: () => any;
}>();
const { t } = useI18n();
</script>

<template>
  <div v-if="finished">
    <slot name="finished">
      {{ t('transactions.query_all.done_group') }}
    </slot>
  </div>
  <div v-else>
    <slot name="running">
      {{ t('transactions.query_all.group') }}
    </slot>
  </div>
</template>
