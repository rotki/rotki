<script setup lang="ts">
const { tooltip, compact = false, disabled = false, labelled = false } = defineProps<{
  tooltip?: string;
  compact?: boolean;
  disabled?: boolean;
  /** The field beside it carries a label on top, so the button drops to the input's line. */
  labelled?: boolean;
}>();

const emit = defineEmits<{
  confirm: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const open = ref<boolean>(false);

const tooltipText = computed<string>(() => tooltip || t('settings.reset_confirm.tooltip'));

function confirm(): void {
  set(open, false);
  emit('confirm');
}

function cancel(): void {
  set(open, false);
}
</script>

<template>
  <RuiMenu
    v-model="open"
    :class-names="{ menu: 'max-w-56' }"
    :options="{ placement: 'top' }"
  >
    <template #activator="{ attrs }">
      <RuiTooltip
        :options="{ placement: 'top' }"
        :open-delay="400"
        :disabled="open"
      >
        <template #activator>
          <RuiButton
            :class="[compact ? 'ml-1' : 'ml-2', { 'mt-1': !compact && !labelled, 'mt-6': !compact && labelled, 'mt-6.5': compact && labelled }]"
            variant="text"
            icon
            :size="compact ? 'sm' : undefined"
            :disabled="disabled"
            v-bind="attrs"
          >
            <RuiIcon name="lu-history" />
          </RuiButton>
        </template>
        {{ tooltipText }}
      </RuiTooltip>
    </template>
    <div class="p-3">
      <p class="text-body-2 mb-3">
        {{ t('settings.reset_confirm.message') }}
      </p>
      <div class="flex justify-end gap-2">
        <RuiButton
          size="sm"
          variant="text"
          @click="cancel()"
        >
          {{ t('settings.reset_confirm.cancel') }}
        </RuiButton>
        <RuiButton
          size="sm"
          color="primary"
          @click="confirm()"
        >
          {{ t('settings.reset_confirm.confirm') }}
        </RuiButton>
      </div>
    </div>
  </RuiMenu>
</template>
