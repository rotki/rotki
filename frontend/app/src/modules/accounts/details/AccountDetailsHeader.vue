<script setup lang="ts">
import type { BlockchainAccountGroupWithBalance } from '@/modules/accounts/blockchain-accounts';
import { getAccountAddress, getGroupId } from '@/modules/accounts/account-utils';
import AccountChains from '@/modules/accounts/AccountChains.vue';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useScramble } from '@/modules/settings/use-scramble';
import LabeledAddressDisplay from '@/modules/shell/components/display/LabeledAddressDisplay.vue';
import TagDisplay from '@/modules/tags/TagDisplay.vue';

/** Chains switched off per group; the chips toggle it, so the drawer and the row stay in step. */
const chainFilter = defineModel<Record<string, string[]>>('chainFilter', { required: true });

const { group } = defineProps<{
  group: BlockchainAccountGroupWithBalance;
}>();

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { scrambleAddress } = useScramble();

const address = computed<string>(() => getAccountAddress(group));

const shownAddress = computed<string>(() => scrambleAddress(get(address)));

/** The chips key the chain filter by the row id, which for a group row is its group id. */
const chainsRow = computed<{ chains: string[]; id: string }>(() => ({ chains: group.chains, id: getGroupId(group) }));

const shortAddress = computed<string>(() => truncateAddress(get(shownAddress), 8));

const closeButton = useTemplateRef<{ $el: HTMLElement }>('closeButton');

/** Puts focus on the close control, the first stop for a keyboard user entering the drawer. */
function focusClose(): void {
  get(closeButton)?.$el.focus();
}

defineExpose({
  focusClose,
});
</script>

<template>
  <div class="flex flex-col gap-2 px-4 py-3 border-b border-default">
    <div class="flex items-start gap-3">
      <div class="flex-1 min-w-0">
        <LabeledAddressDisplay :account="group" />
      </div>
      <div class="flex flex-col items-end">
        <span class="text-caption text-rui-text-secondary">{{ t('common.total') }}</span>
        <FiatDisplay
          :value="group.value"
          class="font-medium"
          data-testid="account-details-value"
        />
      </div>
      <RuiButton
        ref="closeButton"
        variant="text"
        icon
        :aria-label="t('common.actions.close')"
        data-testid="account-details-close"
        @click="emit('close')"
      >
        <RuiIcon name="lu-x" />
      </RuiButton>
    </div>
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <span
        class="font-mono text-caption text-rui-text-secondary"
        :title="shownAddress"
        data-testid="account-details-address"
      >
        {{ shortAddress }}
      </span>
      <AccountChains
        v-model:chain-filter="chainFilter"
        :address="address"
        :row="chainsRow"
      />
      <TagDisplay
        v-if="group.tags && group.tags.length > 0"
        :tags="group.tags"
        small
        class="mt-0!"
      />
    </div>
  </div>
</template>
