<script setup lang="ts">
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

const { chainId, chainName, size = '24px' } = defineProps<{
  chainId: string;
  chainName: string;
  size?: string;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    :open-delay="300"
  >
    <template #activator>
      <div class="relative inline-flex shrink-0">
        <ChainIcon
          :chain="chainId"
          :size="size"
          class="grayscale opacity-60"
        />
        <div
          class="absolute -bottom-1 -right-1 flex items-center justify-center rounded-full bg-rui-error text-white p-[2px] border border-rui-bg"
        >
          <RuiIcon
            name="lu-ban"
            size="10"
          />
        </div>
      </div>
    </template>
    {{ t('general_settings.disabled_chain_queries.entire_chain_tooltip', { chain: chainName }) }}
  </RuiTooltip>
</template>
