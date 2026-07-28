<script setup lang="ts">
const { hours, tolerance, explanation, canWiden = true } = defineProps<{
  /** The time range the fruitless search used, in hours. */
  hours: string;
  /** The amount tolerance the fruitless search used, as a percentage. */
  tolerance: string;
  /** Why no match can exist at all, when that is already known (e.g. an untracked counterpart). */
  explanation?: string;
  /** False once both criteria sit at their ceiling and there is nothing left to widen. */
  canWiden?: boolean;
}>();

const emit = defineEmits<{
  widen: [];
}>();

const { t } = useI18n({ useScope: 'global' });

/** With no match possible, widening the search is busywork - the row needs a decision instead. */
const unmatchable = computed<boolean>(() => !!explanation);

const showWiden = computed<boolean>(() => !get(unmatchable) && canWiden);
</script>

<template>
  <div
    class="flex flex-col items-center gap-2 rounded border border-dashed border-default px-4 py-6 text-center"
    data-testid="potential-matches-empty"
  >
    <RuiIcon
      name="lu-search-x"
      size="28"
      class="text-rui-text-disabled"
    />

    <p class="text-body-2 font-medium text-rui-text">
      {{ t('asset_movement_matching.dialog.empty.title', { hours, tolerance }) }}
    </p>

    <p class="text-caption text-rui-text-secondary max-w-[34ch]">
      {{ explanation ?? t('asset_movement_matching.dialog.empty.hint') }}
    </p>

    <RuiButton
      v-if="showWiden"
      size="sm"
      variant="outlined"
      color="primary"
      data-testid="potential-matches-widen"
      @click="emit('widen')"
    >
      <template #prepend>
        <RuiIcon
          name="lu-scan-search"
          size="16"
        />
      </template>
      {{ t('asset_movement_matching.dialog.empty.widen') }}
    </RuiButton>
  </div>
</template>
