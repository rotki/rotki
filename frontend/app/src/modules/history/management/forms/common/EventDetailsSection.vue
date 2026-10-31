<script setup lang="ts">
/**
 * The collapsed "advanced" section of an event form, for the fields most users never change.
 *
 * @remarks
 * A rejected save scrolls to its first error, which cannot reach a field inside a closed section.
 * So the section opens by itself as soon as one of its fields shows an error, and its header counts
 * them while it is closed.
 */
defineOptions({
  inheritAttrs: false,
});

const { errors, paths } = defineProps<{
  /** The form's error lookup, by dotted path. */
  errors: (path: string) => string[];
  /** The paths of the fields inside the section. */
  paths: readonly string[];
}>();

defineSlots<{
  default: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const OPEN = 0;
const CLOSED = -1;

const openIndex = ref<number>(CLOSED);

const errorCount = computed<number>(() => paths.filter(path => errors(path).length > 0).length);

watch(errorCount, (count, previous) => {
  if (count > 0 && previous === 0)
    set(openIndex, OPEN);
});
</script>

<template>
  <RuiAccordions v-model="openIndex">
    <RuiAccordion
      v-bind="$attrs"
      :class-names="{ header: 'py-4' }"
      eager
    >
      <template #header>
        <div class="flex items-center gap-2">
          {{ t('transactions.events.form.advanced') }}
          <RuiChip
            v-if="errorCount > 0"
            size="sm"
            color="error"
            data-testid="event-details-error-count"
          >
            {{ errorCount }}
          </RuiChip>
        </div>
      </template>
      <div class="py-2">
        <slot />
      </div>
    </RuiAccordion>
  </RuiAccordions>
</template>
