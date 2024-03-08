<script setup lang="ts">
withDefaults(
  defineProps<{
    tooltip: string;
    loading?: boolean;
    disabled?: boolean;
  }>(),
  {
    loading: false,
    disabled: false,
  },
);

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

const refresh = () => emit('refresh');

const slots = useSlots();
const css = useCssModule();
</script>

<template>
  <RefreshButton
    v-if="!slots.refreshMenu"
    :loading="loading"
    :disabled="disabled"
    :tooltip="tooltip"
    @refresh="refresh()"
  />
  <div
    v-else
    class="relative pr-1"
  >
    <VMenu
      offset-y
      :close-on-content-click="false"
    >
      <template #activator="{ on }">
        <RefreshButton
          :loading="loading"
          :disabled="disabled"
          :tooltip="tooltip"
          @refresh="refresh()"
        />
        <RuiButton
          :disabled="disabled"
          :class="css.expander"
          icon
          variant="text"
          size="sm"
          v-on="on"
        >
          <RuiIcon
            size="16"
            name="arrow-down-s-line"
          />
        </RuiButton>
      </template>
      <slot name="refreshMenu" />
    </VMenu>
  </div>
</template>

<style lang="scss" module>
.expander {
  @apply z-[2] text-black -right-2 top-4 w-4 h-4 lg:w-[1.125rem] lg:h-[1.125rem];
  @apply p-0 absolute bg-black/[.12] dark:bg-black dark:text-white #{!important};
}
</style>
