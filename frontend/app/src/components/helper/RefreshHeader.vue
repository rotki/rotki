<script setup lang="ts">
const props = defineProps({
  title: { required: true, type: String },
  loading: { required: true, type: Boolean }
});

const emit = defineEmits(['refresh']);

const { title } = toRefs(props);
const { t } = useI18n();

const tooltip = computed(() => ({
  title: get(title).toLocaleLowerCase()
}));

const refresh = () => {
  emit('refresh');
};
</script>

<template>
  <VRow justify="space-between" align="center" no-gutters>
    <VCol>
      <CardTitle>{{ title }}</CardTitle>
    </VCol>
    <VCol cols="auto">
      <VRow no-gutters>
        <VCol v-if="$slots.actions" cols="auto" class="px-1">
          <slot name="actions" />
        </VCol>
        <VCol cols="auto" class="px-1">
          <RefreshButton
            :loading="loading"
            :tooltip="t('helpers.refresh_header.tooltip', tooltip)"
            @refresh="refresh()"
          />
        </VCol>
        <VCol v-if="$slots.default" cols="auto" class="px-1">
          <slot />
        </VCol>
      </VRow>
    </VCol>
  </VRow>
</template>
