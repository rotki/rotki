<script setup lang="ts">
import { useCopy } from '@/composables/copy';

const props = defineProps<{
  tooltip?: string | null;
  disabled?: boolean;
  value: string;
}>();

defineSlots<{
  default: () => any;
  tooltip: () => any;
  label: () => any;
}>();

const { t } = useI18n();

const { value } = toRefs(props);

const { copied, copy } = useCopy(value);
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    :open-delay="200"
    class="text-no-wrap"
    :class="{ 'cursor-pointer': !disabled }"
    :disabled="disabled"
    @click="copy()"
  >
    <template #activator>
      <slot />
    </template>

    <div
      class="text-center"
      data-cy="display-full-value"
    >
      <slot name="tooltip">
        <div v-if="tooltip">
          {{ tooltip }}
        </div>
      </slot>
      <div class="uppercase font-bold text-caption overflow-hidden h-5">
        <div
          class="transition-all duration-100"
          :class="{
            '-mt-5': copied,
          }"
        >
          <slot name="label">
            {{ t('amount_display.click_to_copy') }}
          </slot>
        </div>
        <div class="text-rui-success-lighter">
          {{ t('amount_display.copied') }}
        </div>
      </div>
    </div>
  </RuiTooltip>
</template>
