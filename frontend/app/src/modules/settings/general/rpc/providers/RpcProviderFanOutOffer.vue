<script setup lang="ts">
import type { RpcProviderCandidate } from '@/modules/settings/general/rpc/providers/rpc-provider-plan';
import RpcProviderCandidateRow from '@/modules/settings/general/rpc/providers/RpcProviderCandidateRow.vue';

const modelEnabled = defineModel<boolean>({ required: true });

const {
  candidates,
  enablement = '',
  provider,
  selected,
  unreadable = '',
  unsupported = '',
} = defineProps<{
  /** Every other chain the provider serves, those already holding the key included. */
  candidates: RpcProviderCandidate[];
  enablement?: string;
  preparing?: boolean;
  /** The provider's own name, which is what the offer is worth naming. */
  provider: string;
  selected: readonly string[];
  unreadable?: string;
  unsupported?: string;
}>();

const emit = defineEmits<{
  toggle: [change: { chain: string; checked: boolean }];
}>();

const { t } = useI18n({ useScope: 'global' });

const addable = computed<number>(() => candidates.filter(candidate => !candidate.existing).length);
const count = computed<number>(() => selected.length);
</script>

<template>
  <RuiAlert
    type="info"
    class="mb-4"
    data-testid="provider-fan-out-offer"
  >
    <div class="flex flex-col gap-1">
      <span>{{ t('rpc_provider_setup.offer.hint', { provider }) }}</span>
      <RuiCheckbox
        v-model="modelEnabled"
        color="primary"
        hide-details
        size="sm"
        data-testid="provider-fan-out-enable"
      >
        <span class="text-sm">{{ t('rpc_provider_setup.offer.enable', { count: addable, provider }, addable) }}</span>
      </RuiCheckbox>

      <div
        v-if="modelEnabled"
        class="pl-8 flex flex-col gap-2"
      >
        <RuiProgress
          v-if="preparing"
          circular
          variant="indeterminate"
          size="16"
          color="primary"
        />
        <div
          v-else-if="addable === 0"
          class="text-sm"
          data-testid="provider-nothing-to-add"
        >
          {{ t('rpc_provider_setup.select.none', { provider }) }}
        </div>
        <template v-else>
          <RuiAccordions>
            <RuiAccordion
              eager
              header-grow
              :class-names="{ header: 'p-0', content: 'pt-2' }"
              data-testid="provider-chain-picker"
            >
              <template #header>
                <span
                  class="text-sm"
                  data-testid="provider-selection-summary"
                >
                  {{ t('rpc_provider_setup.select.picker', { count, total: addable }) }}
                </span>
              </template>
              <div class="flex flex-col">
                <RpcProviderCandidateRow
                  v-for="candidate in candidates"
                  :key="candidate.chain"
                  :candidate="candidate"
                  :selected="selected.includes(candidate.chain)"
                  @toggle="emit('toggle', { chain: candidate.chain, checked: $event })"
                />
              </div>
            </RuiAccordion>
          </RuiAccordions>
          <!-- Outside the accordion: its height is a measured pixel value with the overflow hidden,
               so a line added to it after the measurement is clipped in half. -->
          <p
            v-if="unsupported"
            class="text-xs text-rui-text-secondary"
            data-testid="provider-unsupported"
          >
            {{ t('rpc_provider_setup.select.unsupported', { chains: unsupported, provider }) }}
          </p>
          <p
            v-if="unreadable"
            class="text-xs text-rui-text-secondary"
            data-testid="provider-unreadable"
          >
            {{ t('rpc_provider_setup.select.unreadable', { chains: unreadable }) }}
          </p>
          <p
            v-if="enablement"
            class="text-xs text-rui-text-secondary"
            data-testid="provider-enablement"
          >
            {{ enablement }}
          </p>
        </template>
      </div>
    </div>
  </RuiAlert>
</template>
