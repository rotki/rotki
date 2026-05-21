<script setup lang="ts">
import type { Rule, RuleDraft } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chain-queries-state';
import ChainDisplay from '@/modules/accounts/blockchain/ChainDisplay.vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useRuleEditorForm } from '@/modules/settings/general/disabled-chain-queries/use-rule-editor-form';
import AccountDisplay from '@/modules/shell/components/display/AccountDisplay.vue';

const open = defineModel<boolean>('open', { required: true });

const { editing } = defineProps<{
  editing?: Rule;
}>();

const emit = defineEmits<{
  save: [payload: { draft: RuleDraft; id: string | undefined }];
}>();

const { t } = useI18n({ useScope: 'global' });

const { accounts } = storeToRefs(useBlockchainAccountsStore());
const { supportedChains } = useSupportedChains();

const {
  address,
  addressOptions,
  availableChainsForAddress,
  buildDraft,
  canSave,
  chainId,
  kind,
  reset,
  scope,
  selectedChainIds,
} = useRuleEditorForm({
  accounts,
  chains: supportedChains,
  editing: () => editing,
});

const chainOptionsForAddress = computed(() => get(supportedChains).filter(c => get(availableChainsForAddress).includes(c.id)));

function onSave(): void {
  const draft = buildDraft();
  if (!draft)
    return;
  emit('save', { draft, id: editing?.id });
  set(open, false);
}

watch(open, (value) => {
  if (value)
    reset();
});
</script>

<template>
  <RuiDialog
    v-model="open"
    max-width="560"
  >
    <RuiCard>
      <template #header>
        {{ editing ? t('general_settings.disabled_chain_queries.dialog.title_edit') : t('general_settings.disabled_chain_queries.dialog.title_add') }}
      </template>

      <div class="flex flex-col gap-4">
        <div>
          <div class="text-rui-text-secondary text-caption mb-2">
            {{ t('general_settings.disabled_chain_queries.dialog.kind_label') }}
          </div>
          <RuiButtonGroup
            v-model="kind"
            color="primary"
            variant="outlined"
            required
            data-testid="rule-kind-toggle"
          >
            <RuiButton model-value="chain">
              {{ t('general_settings.disabled_chain_queries.dialog.kind_chain') }}
            </RuiButton>
            <RuiButton model-value="address">
              {{ t('general_settings.disabled_chain_queries.dialog.kind_address') }}
            </RuiButton>
          </RuiButtonGroup>
        </div>

        <RuiAutoComplete
          v-if="kind === 'chain'"
          v-model="chainId"
          :options="supportedChains"
          :label="t('general_settings.disabled_chain_queries.dialog.chain_label')"
          variant="outlined"
          key-attr="id"
          text-attr="name"
          hide-details
          auto-select-first
          data-testid="rule-chain-picker"
        >
          <template #selection="{ item }">
            <ChainDisplay
              dense
              :chain="item.id"
            />
          </template>
          <template #item="{ item }">
            <ChainDisplay
              dense
              :chain="item.id"
            />
          </template>
        </RuiAutoComplete>

        <template v-else>
          <RuiAutoComplete
            v-model="address"
            :options="addressOptions"
            :label="t('general_settings.disabled_chain_queries.dialog.address_label')"
            variant="outlined"
            key-attr="address"
            text-attr="address"
            hide-details
            auto-select-first
            data-testid="rule-address-picker"
          >
            <template #selection="{ item }">
              <AccountDisplay
                hide-chain-icon
                :account="{ address: item.address, chain: item.chainIds[0] }"
              />
            </template>
            <template #item="{ item }">
              <div class="flex flex-col py-1">
                <AccountDisplay
                  hide-chain-icon
                  :account="{ address: item.address, chain: item.chainIds[0] }"
                />
                <div class="text-caption text-rui-text-secondary">
                  {{ t('general_settings.disabled_chain_queries.dialog.address_tracked_on', { count: item.chainIds.length }) }}
                </div>
              </div>
            </template>
          </RuiAutoComplete>

          <div>
            <div class="text-rui-text-secondary text-caption mb-2">
              {{ t('general_settings.disabled_chain_queries.dialog.scope_label') }}
            </div>
            <RuiButtonGroup
              v-model="scope"
              color="primary"
              variant="outlined"
              required
              data-testid="rule-scope-toggle"
            >
              <RuiButton model-value="all">
                {{ t('general_settings.disabled_chain_queries.dialog.scope_all') }}
              </RuiButton>
              <RuiButton model-value="specific">
                {{ t('general_settings.disabled_chain_queries.dialog.scope_specific') }}
              </RuiButton>
            </RuiButtonGroup>
          </div>

          <RuiAutoComplete
            v-if="scope === 'specific'"
            :model-value="selectedChainIds"
            :options="chainOptionsForAddress"
            :label="t('general_settings.disabled_chain_queries.dialog.chains_label')"
            variant="outlined"
            key-attr="id"
            text-attr="name"
            chips
            hide-details
            auto-select-first
            data-testid="rule-chains-picker"
            @update:model-value="selectedChainIds = $event"
          >
            <template #selection="{ item }">
              <ChainDisplay
                dense
                :chain="item.id"
              />
            </template>
            <template #item="{ item }">
              <ChainDisplay
                dense
                :chain="item.id"
              />
            </template>
          </RuiAutoComplete>
        </template>
      </div>

      <template #footer>
        <div class="grow" />
        <RuiButton
          variant="text"
          @click="open = false"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          color="primary"
          :disabled="!canSave"
          data-testid="rule-save"
          @click="onSave()"
        >
          {{ t('common.actions.save') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
