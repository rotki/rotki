<script setup lang="ts">
import type { RpcProviderCandidate } from '@/modules/settings/general/rpc/providers/rpc-provider-plan';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

const { candidate, selected } = defineProps<{
  candidate: RpcProviderCandidate;
  selected: boolean;
}>();

const emit = defineEmits<{
  toggle: [checked: boolean];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getChainName } = useSupportedChains();
</script>

<template>
  <div
    class="flex items-center gap-2 py-0.5"
    data-testid="provider-candidate"
  >
    <!-- The chain rides inside the checkbox's own label, so it is both the accessible name and part
         of the hit target. -->
    <RuiCheckbox
      :model-value="selected"
      :disabled="!!candidate.existing"
      color="primary"
      hide-details
      size="sm"
      @update:model-value="emit('toggle', $event)"
    >
      <span class="flex items-center gap-2 min-w-0">
        <ChainIcon
          :chain="candidate.chain"
          size="20px"
        />
        <span class="text-sm truncate">{{ getChainName(candidate.chain) }}</span>
      </span>
    </RuiCheckbox>
    <span
      v-if="candidate.existing"
      class="ml-auto text-xs text-rui-text-secondary"
    >
      {{ t('rpc_provider_setup.select.already_added') }}
    </span>
    <span
      v-else-if="candidate.outdated"
      class="ml-auto text-xs text-rui-primary"
    >
      {{ t('rpc_provider_setup.select.replaces_key', { node: candidate.outdated.name }) }}
    </span>
  </div>
</template>
