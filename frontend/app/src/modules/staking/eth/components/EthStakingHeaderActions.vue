<script setup lang="ts">
import ActiveModules from '@/components/defi/ActiveModules.vue';
import { Module } from '@/types/modules';

interface Props {
  refreshing: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center gap-3">
    <ActiveModules :modules="[Module.ETH2]" />

    <RuiTooltip :open-delay="400">
      <template #activator>
        <RuiButton
          variant="outlined"
          color="primary"
          :loading="refreshing"
          @click="emit('refresh')"
        >
          <template #prepend>
            <RuiIcon name="lu-refresh-ccw" />
          </template>
          {{ t('common.refresh') }}
        </RuiButton>
      </template>
      {{ t('premium_components.staking.refresh') }}
    </RuiTooltip>
  </div>
</template>
