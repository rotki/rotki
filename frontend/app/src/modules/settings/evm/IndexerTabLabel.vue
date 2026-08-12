<script setup lang="ts">
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

interface TabItem {
  id: string;
  isDefault: boolean;
  name?: string;
}

defineProps<{
  tab: TabItem;
}>();

const emit = defineEmits<{
  remove: [id: string];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center gap-2">
    <template v-if="tab.isDefault">
      <RuiIcon
        name="lu-globe"
        size="16"
      />
      <span>{{ t('evm_settings.indexer.default_tab') }}</span>
    </template>
    <template v-else>
      <ChainIcon
        :chain="tab.id"
        size="16px"
      />
      <span>{{ tab.name }}</span>
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            size="sm"
            class="!p-0.5"
            data-testid="remove-chain"
            :data-key="tab.id"
            @click.stop="emit('remove', tab.id)"
          >
            <RuiIcon
              name="lu-x"
              size="14"
            />
          </RuiButton>
        </template>
        {{ t('evm_settings.indexer.remove_chain') }}
      </RuiTooltip>
    </template>
  </div>
</template>
