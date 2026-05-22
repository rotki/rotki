<script setup lang="ts">
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import SettingsStatusMessage from '@/modules/settings/controls/SettingsStatusMessage.vue';
import DisabledChainIcon from '@/modules/settings/general/disabled-chain-queries/DisabledChainIcon.vue';
import DisabledChainQueryRuleDialog from '@/modules/settings/general/disabled-chain-queries/DisabledChainQueryRuleDialog.vue';
import RuleChainIcons from '@/modules/settings/general/disabled-chain-queries/RuleChainIcons.vue';
import {
  type DisabledChainQueries,
  type Rule,
  type RuleDraft,
  useDisabledChainQueriesState,
} from '@/modules/settings/general/disabled-chain-queries/use-disabled-chain-queries-state';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import AccountDisplay from '@/modules/shell/components/display/AccountDisplay.vue';

const { t } = useI18n({ useScope: 'global' });

const { disabledChainQueries } = storeToRefs(useGeneralSettingsStore());
const { matchChain, supportedChains } = useSupportedChains();

const {
  addRule,
  removeRule,
  rules,
  updateRule,
} = useDisabledChainQueriesState({
  matchChain,
  ready: (): boolean => get(supportedChains).length > 0,
  source: disabledChainQueries,
});

const dialogOpen = ref<boolean>(false);
const editing = ref<Rule>();

function commit(
  payload: DisabledChainQueries | undefined,
  updateImmediate: (value: DisabledChainQueries) => void,
): void {
  if (payload !== undefined)
    updateImmediate(payload);
}

function openCreate(): void {
  set(editing, undefined);
  set(dialogOpen, true);
}

function openEdit(rule: Rule): void {
  set(editing, rule);
  set(dialogOpen, true);
}

function onSave(
  draft: RuleDraft,
  id: string | undefined,
  updateImmediate: (value: DisabledChainQueries) => void,
): void {
  const payload = id === undefined ? addRule(draft) : updateRule(id, draft);
  commit(payload, updateImmediate);
}

function onRemove(
  id: string,
  updateImmediate: (value: DisabledChainQueries) => void,
): void {
  commit(removeRule(id), updateImmediate);
}

function chainNameFor(chainId: string): string {
  return get(supportedChains).find(c => c.id === chainId)?.name ?? chainId;
}

function entireChainLabel(chainId: string): string {
  return `${chainNameFor(chainId)} — ${t('general_settings.disabled_chain_queries.scope.entire_chain')}`;
}

function onSavePayload(
  payload: { draft: RuleDraft; id: string | undefined },
  updateImmediate: (value: DisabledChainQueries) => void,
): void {
  onSave(payload.draft, payload.id, updateImmediate);
}
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate, loading }"
    setting="disabledChainQueries"
    :error-message="t('general_settings.disabled_chain_queries.validation.error')"
    :success-message="t('general_settings.disabled_chain_queries.validation.success')"
  >
    <div class="flex flex-col gap-3">
      <div
        v-if="rules.length === 0"
        data-testid="disabled-chain-queries-empty"
        class="text-rui-text-secondary text-caption border border-dashed border-default rounded-md p-4 text-center"
      >
        {{ t('general_settings.disabled_chain_queries.empty') }}
      </div>

      <div
        v-for="rule in rules"
        :key="rule.id"
        :data-testid="`rule-${rule.id}`"
        class="flex items-center justify-between gap-2 border border-default rounded-md p-3"
      >
        <div class="flex items-center gap-3 min-w-0">
          <template v-if="rule.kind === 'chain'">
            <DisabledChainIcon
              :chain-id="rule.chainId"
              :chain-name="chainNameFor(rule.chainId)"
            />
            <span class="text-rui-text-secondary text-sm">{{ entireChainLabel(rule.chainId) }}</span>
          </template>
          <template v-else>
            <AccountDisplay
              hide-chain-icon
              :account="{ address: rule.address, chain: rule.chainIds[0] }"
            />
            <RuleChainIcons
              :chain-ids="rule.chainIds"
              :chain-name-for="chainNameFor"
              :empty-label="t('general_settings.disabled_chain_queries.scope.no_chains')"
            />
          </template>
        </div>
        <div class="flex items-center gap-1 shrink-0">
          <RuiButton
            variant="text"
            icon
            size="sm"
            :disabled="loading"
            :data-testid="`rule-edit-${rule.id}`"
            @click="openEdit(rule)"
          >
            <RuiIcon
              name="lu-pencil"
              size="18"
            />
          </RuiButton>
          <RuiButton
            variant="text"
            icon
            size="sm"
            color="error"
            :disabled="loading"
            :data-testid="`rule-remove-${rule.id}`"
            @click="onRemove(rule.id, updateImmediate)"
          >
            <RuiIcon
              name="lu-trash-2"
              size="18"
            />
          </RuiButton>
        </div>
      </div>

      <div>
        <RuiButton
          variant="outlined"
          color="primary"
          :disabled="loading"
          data-testid="rule-add"
          @click="openCreate()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-plus"
              size="18"
            />
          </template>
          {{ t('general_settings.disabled_chain_queries.add_rule') }}
        </RuiButton>
      </div>

      <DisabledChainQueryRuleDialog
        v-model:open="dialogOpen"
        :editing="editing"
        @save="onSavePayload($event, updateImmediate)"
      />

      <SettingsStatusMessage
        :error="error"
        :success="success"
        data-testid="disabled-chain-queries-status"
      />
    </div>
  </SettingsOption>
</template>
