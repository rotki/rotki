<script setup lang="ts">
import type { InteractionNode } from './address-interaction-graph';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import { useInteractionLabels } from './use-interaction-labels';

const { node } = defineProps<{ node: InteractionNode }>();

const emit = defineEmits<{
  'clear': [];
  'find-path': [];
  'hide': [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { namedChain } = useInteractionLabels();
</script>

<template>
  <div
    class="flex flex-col gap-3 border-b border-default p-4"
    data-testid="interaction-panel-node"
  >
    <div class="flex items-center justify-between gap-2">
      <h3 class="text-xs font-medium text-rui-text-secondary">
        {{ t('address_interactions.selected_address') }}
      </h3>
      <RuiButton
        variant="text"
        icon
        size="sm"
        class="-my-1 text-rui-text-secondary!"
        :aria-label="t('address_interactions.clear_selection')"
        data-testid="interaction-panel-clear-node"
        @click="emit('clear')"
      >
        <RuiIcon
          name="lu-x"
          size="16"
        />
      </RuiButton>
    </div>
    <HashLink
      :text="node.address"
      :location="namedChain(node)"
      :size="14"
    />
    <div class="flex flex-wrap items-center gap-1">
      <LocationIcon
        v-for="chain in node.chains"
        :key="chain"
        :item="chain"
        icon
        size="16px"
      />
    </div>
    <div class="flex flex-wrap gap-2">
      <RuiButton
        color="primary"
        size="sm"
        data-testid="interaction-find-path"
        @click="emit('find-path')"
      >
        <template #prepend>
          <RuiIcon
            name="lu-route"
            size="16"
          />
        </template>
        {{ t('address_interactions.path.find') }}
      </RuiButton>
      <RuiButton
        variant="outlined"
        size="sm"
        data-testid="interaction-hide-node"
        @click="emit('hide')"
      >
        <template #prepend>
          <RuiIcon
            name="lu-eye-off"
            size="16"
          />
        </template>
        {{ t('address_interactions.hide') }}
      </RuiButton>
    </div>
  </div>
</template>
