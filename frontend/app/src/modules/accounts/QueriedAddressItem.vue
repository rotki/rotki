<script setup lang="ts">
import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import { RuiButton, RuiIcon, RuiTooltip } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import LabeledAddressDisplay from '@/modules/shell/components/display/LabeledAddressDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import TagDisplay from '@/modules/tags/TagDisplay.vue';

defineProps<{
  address: string;
  /** The tracked account behind the address, or `undefined` when the address outlived it. */
  account: BlockchainAccount | undefined;
}>();

const emit = defineEmits<{ remove: [] }>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div
    class="flex items-center gap-3 px-3 py-2"
    data-testid="queried-address-row"
  >
    <div class="flex-1 min-w-0">
      <template v-if="account">
        <LabeledAddressDisplay :account="account" />
        <TagDisplay
          :tags="account.tags"
          small
        />
      </template>
      <template v-else>
        <HashLink
          :text="address"
          location="ethereum"
        />
        <div class="text-xs text-rui-text-secondary">
          {{ t('queried_address_dialog.untracked') }}
        </div>
      </template>
    </div>
    <RuiTooltip
      :options="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          variant="text"
          icon
          size="sm"
          color="error"
          data-testid="queried-address-remove"
          @click="emit('remove')"
        >
          <RuiIcon
            size="16"
            name="lu-trash-2"
          />
        </RuiButton>
      </template>

      {{ t('queried_address_dialog.remove_tooltip') }}
    </RuiTooltip>
  </div>
</template>
