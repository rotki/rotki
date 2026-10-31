<script setup lang="ts">
import type { InteractionNode } from './address-interaction-graph';
import type { InteractionPath } from './interaction-clusters';
import AddressInteractionAddress from './AddressInteractionAddress.vue';
import { useInteractionLabels } from './use-interaction-labels';

/** How two addresses are tied together: each address on the shortest path, and what links it to the next. */
const { path, from, to } = defineProps<{
  path?: InteractionPath;
  from: InteractionNode;
  to: InteractionNode;
}>();

const emit = defineEmits<{
  back: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { activitySummary, shortAddressLabel } = useInteractionLabels();

interface PathStep {
  node: InteractionNode;
  link?: string;
}

const steps = computed<PathStep[]>(() => (path?.nodes ?? []).map((node, index) => {
  const connection = path?.connections[index];
  return { link: connection ? activitySummary(connection) : undefined, node };
}));

const ends = computed<{ from: string; to: string }>(() => ({ from: shortAddressLabel(from), to: shortAddressLabel(to) }));
</script>

<template>
  <div
    class="flex min-w-0 flex-col gap-3 p-4 pt-2"
    data-testid="interaction-path"
  >
    <RuiButton
      variant="text"
      size="sm"
      class="-ml-2 self-start"
      data-testid="interaction-path-back"
      @click="emit('back')"
    >
      <template #prepend>
        <RuiIcon
          name="lu-arrow-left"
          size="14"
        />
      </template>
      {{ t('common.actions.back') }}
    </RuiButton>
    <div aria-live="polite">
      <h3 class="text-base font-semibold">
        {{ path ? t('address_interactions.path.linked', { count: path.connections.length }, path.connections.length) : t('address_interactions.path.not_linked') }}
      </h3>
      <p class="mt-1 text-sm text-rui-text-secondary">
        {{ path ? t('address_interactions.path.linked_help', ends) : t('address_interactions.path.not_linked_help', ends) }}
      </p>
    </div>
    <ol
      v-if="path"
      class="flex flex-col pl-0"
    >
      <li
        v-for="step in steps"
        :key="step.node.id"
        class="flex flex-col"
        data-testid="interaction-path-step"
      >
        <span class="flex min-h-8 items-center gap-2 text-sm font-medium">
          <RuiIcon
            name="lu-wallet"
            size="16"
            class="shrink-0 text-rui-text-secondary"
          />
          <AddressInteractionAddress
            :node="step.node"
            class="truncate"
          />
        </span>
        <span
          v-if="step.link"
          class="ml-2 border-l-2 border-rui-primary/40 py-1 pl-4 text-xs text-rui-text-secondary"
        >
          {{ step.link }}
        </span>
      </li>
    </ol>
  </div>
</template>
