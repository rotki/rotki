<script setup lang="ts">
const props = defineProps<{
  value: boolean;
  count: number;
}>();

const emit = defineEmits(['input']);

const css = useCssModule();

const { value } = toRefs(props);
const input = () => {
  emit('input', !get(value));
};

const { t } = useI18n();
</script>

<template>
  <Card outlined :class="css.collapsed">
    <VRow no-gutters align="center">
      <VCol cols="auto">
        <VIcon color="primary">mdi-spin mdi-loading</VIcon>
      </VCol>
      <VCol>
        <div :class="css.title">
          {{ t('collapsed_pending_tasks.title', { count }, count) }}
        </div>
      </VCol>

      <VCol cols="auto">
        <RuiButton icon variant="text" size="sm" @click="input()">
          <VIcon v-if="value">mdi-chevron-up</VIcon>
          <VIcon v-else>mdi-chevron-down</VIcon>
        </RuiButton>
      </VCol>
    </VRow>
  </Card>
</template>

<style module lang="scss">
.collapsed {
  margin-left: 8px;
  margin-bottom: 8px;
}

.title {
  font-size: 16px;
  padding-left: 1.4rem;
}
</style>
