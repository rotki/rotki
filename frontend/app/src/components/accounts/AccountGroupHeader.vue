<script setup lang="ts">
import { useBreakpoint } from '@rotki/ui-library-compat';
import Fragment from '@/components/helper/Fragment';
import type { BlockchainAccountWithBalance, XpubData } from '@/types/blockchain/accounts';
import type { ComputedRef } from 'vue';

const props = withDefaults(
  defineProps<{
    group: string;
    items: BlockchainAccountWithBalance[];
    expanded: boolean;
    loading?: boolean;
  }>(),
  { loading: false },
);

const emit = defineEmits<{
  (e: 'delete', account: BlockchainAccountWithBalance<XpubData>): void;
  (e: 'expand', account: BlockchainAccountWithBalance<XpubData>): void;
  (e: 'edit', account: BlockchainAccountWithBalance<XpubData>): void;
}>();

const { t } = useI18n();

const { items } = toRefs(props);
const { name: breakpoint, isXs } = useBreakpoint();
const { shouldShowAmount } = storeToRefs(useSessionSettingsStore());

const xpub: ComputedRef<BlockchainAccountWithBalance<XpubData>> = computed(() => {
  const account = get(items).filter(isAccountWithBalanceXpub).find(item => item.groupHeader);
  assert(account);
  return account;
});

const label = computed<string | undefined>(() => get(xpub).label);

const xpubTags = computed<string[] | undefined>(() => get(xpub).tags);

const displayXpub = computed<string>(() =>
  truncateAddress(get(xpub).data.xpub, truncationPoints[get(breakpoint)] ?? 4),
);
</script>

<template>
  <td
    v-if="!group"
    class="font-medium text-subtitle-2 px-4 py-2"
    colspan="5"
  >
    {{ t('account_group_header.standalone') }}
  </td>
  <Fragment v-else>
    <td
      colspan="2"
      :class="{
        '!p-2': !isXs,
      }"
    >
      <div class="pl-9">
        <span class="text-subtitle-2">{{ label }}</span>
      </div>
      <div class="flex items-center gap-1 -my-2">
        <RuiButton
          :disabled="items.length === 0"
          variant="text"
          size="sm"
          icon
          @click="emit('expand', xpub);"
        >
          <RuiIcon
            v-if="expanded"
            name="arrow-up-s-line"
          />
          <RuiIcon
            v-else
            name="arrow-down-s-line"
          />
        </RuiButton>
        <span class="font-medium">
          {{ t('account_group_header.xpub') }}
        </span>
        <span :class="{ blur: !shouldShowAmount }">
          <RuiTooltip
            :popper="{ placement: 'top' }"
            :open-delay="400"
          >
            <template #activator>
              {{ displayXpub }}
            </template>
            {{ xpub.data.xpub }}
          </RuiTooltip>
        </span>
        <CopyButton
          :value="xpub.data.xpub"
          :tooltip="t('account_group_header.copy_tooltip')"
        />
        <span
          v-if="xpub.data.derivationPath"
          :class="{ blur: !shouldShowAmount }"
        >
          <span class="font-medium">
            {{ t('account_group_header.derivation_path') }}:
          </span>
          {{ xpub.data.derivationPath }}
        </span>
      </div>
      <TagDisplay
        wrapper-class="ml-9"
        :tags="xpubTags"
      />
    </td>
    <td class="text-end px-4">
      <AmountDisplay
        :value="xpub.amount"
        :loading="loading"
        :asset="isXs ? 'BTC' : undefined"
        :asset-padding="0.1"
      />
    </td>
    <td class="text-end px-4">
      <AmountDisplay
        fiat-currency="USD"
        show-currency="symbol"
        :value="xpub.usdValue"
        :loading="loading"
        :asset-padding="0.1"
      />
    </td>
    <td class="text-end">
      <RowActions
        :edit-tooltip="t('account_group_header.edit_tooltip')"
        :delete-tooltip="t('account_group_header.delete_tooltip')"
        @edit-click="emit('edit', xpub);"
        @delete-click="emit('delete', xpub);"
      />
    </td>
  </Fragment>
</template>
