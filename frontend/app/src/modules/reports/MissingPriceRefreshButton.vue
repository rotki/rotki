<script setup lang="ts">
const { disabled, loading } = defineProps<{
  disabled: boolean;
  loading: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center gap-1">
    <RuiTooltip
      :options="{ placement: 'right' }"
      :open-delay="700"
      :class-names="{ tooltip: 'max-w-[16rem]' }"
    >
      <template #activator>
        <RuiIcon
          class="mr-1"
          size="20"
          name="lu-triangle-alert"
          color="warning"
        />
      </template>
      <span>
        {{ t('profit_loss_report.actionable.missing_prices.refresh_price_hint') }}
      </span>
    </RuiTooltip>
    <RuiButton
      :disabled="disabled"
      :loading="loading"
      class="-mr-3 !py-[0.625rem] rounded-l-none"
      size="sm"
      color="primary"
      @click="emit('refresh')"
    >
      <RuiIcon
        size="20"
        name="lu-refresh-ccw"
      />
    </RuiButton>
  </div>
</template>
