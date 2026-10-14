<script setup lang="ts">
const { enabled, identifier, label } = defineProps<{
  /** A disabled module queries nothing, so its addresses show but cannot be changed. */
  enabled: boolean;
  identifier: string;
  label: string;
}>();

const emit = defineEmits<{
  manage: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    v-if="enabled"
    :options="{ placement: 'top' }"
    :open-delay="400"
  >
    <template #activator>
      <RuiButton
        variant="text"
        color="primary"
        size="sm"
        class="-ml-2"
        data-testid="module-addresses"
        :data-key="identifier"
        @click="emit('manage')"
      >
        {{ label }}
        <template #append>
          <RuiIcon
            name="lu-pencil"
            size="14"
            class="text-rui-text-secondary"
          />
        </template>
      </RuiButton>
    </template>
    {{ t('module_selector.select_accounts_hint') }}
  </RuiTooltip>
  <span
    v-else
    class="text-sm text-rui-text-disabled"
  >
    {{ label }}
  </span>
</template>
