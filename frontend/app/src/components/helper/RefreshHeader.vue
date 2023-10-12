<script setup lang="ts">
const props = defineProps<{
  title: string;
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

const { title } = toRefs(props);
const { t } = useI18n();

const tooltip = computed(() => ({
  title: get(title).toLocaleLowerCase()
}));

const slots = useSlots();
</script>

<template>
  <div class="flex flex-row items-center justify-between gap-4">
    <CardTitle>{{ title }}</CardTitle>
    <div class="flex flex-row gap-4 items-center">
      <slot v-if="slots.actions" name="actions" />
      <RefreshButton
        :loading="loading"
        :tooltip="t('helpers.refresh_header.tooltip', tooltip)"
        @refresh="emit('refresh')"
      />
      <slot v-if="slots.default" />
    </div>
  </div>
</template>
