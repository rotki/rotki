<script setup lang="ts">
import RefreshButton from '@/components/helper/RefreshButton.vue';

interface SummaryCardRefreshMenuProps {
  tooltip: string;
  loading?: boolean;
  disabled?: boolean;
}
withDefaults(defineProps<SummaryCardRefreshMenuProps>(), {
  disabled: false,
  loading: false,
});

const emit = defineEmits<{
  refresh: [];
}>();

defineSlots<{
  refreshMenu: () => any;
}>();
</script>

<template>
  <RefreshButton
    v-if="!$slots.refreshMenu"
    :loading="loading"
    :disabled="disabled"
    :tooltip="tooltip"
    @refresh="emit('refresh')"
  />
  <div
    v-else
    class="relative pr-1"
  >
    <RuiMenu :popper="{ placement: 'bottom-start' }">
      <template #activator="{ attrs }">
        <RefreshButton
          :loading="loading"
          :disabled="disabled"
          :tooltip="tooltip"
          @refresh="emit('refresh')"
        />
        <RuiButton
          :disabled="disabled"
          class="z-[2] text-black -right-2 top-4 w-4 h-4 lg:w-[1.125rem] lg:h-[1.125rem] !p-0 !absolute !bg-black/[.12] dark:!bg-black dark:text-white"
          icon
          variant="text"
          size="sm"
          v-bind="attrs"
        >
          <RuiIcon
            size="16"
            name="lu-chevron-down"
          />
        </RuiButton>
      </template>
      <slot name="refreshMenu" />
    </RuiMenu>
  </div>
</template>
