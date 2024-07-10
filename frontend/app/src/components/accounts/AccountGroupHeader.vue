<script setup lang="ts">
import { useBreakpoint } from '@rotki/ui-library-compat';
import Fragment from '@/components/helper/Fragment';
import type BigNumber from 'bignumber.js';
import type { BlockchainAccountWithBalance, XpubData } from '@/types/blockchain/accounts';

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
const { scrambleAddress, shouldShowAmount } = useScramble();

const xpub: ComputedRef<BlockchainAccountWithBalance<XpubData>> = computed(() => {
  const account = get(items).filter(isAccountWithBalanceXpub).find(item => item.groupHeader);
  assert(account);
  return account;
});

const label = computed<string | undefined>(() => get(xpub).label);

const xpubTags = computed<string[] | undefined>(() => get(xpub).tags);

const displayXpub = computed<string>(() =>
  scrambleAddress(truncateAddress(get(xpub).data.xpub, truncationPoints[get(breakpoint)] ?? 4)),
);

const amountSum = computed<BigNumber>(() =>
  bigNumberSum(get(items).map(({ amount }) => amount)),
);

const totalAddresses = computed(() => get(items).filter(item => !item.groupHeader).length);

const usdSum = computed<BigNumber>(() => balanceUsdValueSum(get(items)));
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
      class="!p-2"
    >
      <div class="flex items-center gap-4">
        <RuiButton
          :disabled="totalAddresses === 0"
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
        <div>
          <div class="text-subtitle-2">
            {{ label }}
          </div>
          <div class="flex items-center gap-2 -my-2 text-sm">
            <div class="font-medium">
              {{ t('account_group_header.xpub') }}
            </div>
            <div
              class="[&_*]:font-mono"
              :class="{ blur: !shouldShowAmount }"
            >
              <RuiTooltip
                :popper="{ placement: 'top' }"
                :open-delay="400"
                tooltip-class="[&_*]:font-mono"
              >
                <template #activator>
                  {{ displayXpub }}
                </template>
                {{ xpub.data.xpub }}
              </RuiTooltip>
            </div>
            <CopyButton
              :value="xpub.data.xpub"
              :tooltip="t('account_group_header.copy_tooltip')"
            />
            <RuiTooltip>
              <template #activator>
                <RuiChip size="sm">
                  {{ totalAddresses }}
                </RuiChip>
              </template>
              {{ t('account_group_header.addresses', { count: totalAddresses }) }}
            </RuiTooltip>
          </div>
          <div
            v-if="xpub.data.derivationPath"
            class="text-sm"
            :class="{ blur: !shouldShowAmount }"
          >
            <span class="font-medium">
              {{ t('account_group_header.derivation_path') }}:
            </span>
            <span class="font-mono">
              {{ xpub.data.derivationPath }}
            </span>
          </div>
          <TagDisplay
            small
            :tags="xpubTags"
          />
        </div>
      </div>
    </td>
    <td class="text-end px-4">
      <AmountDisplay
        :value="amountSum"
        :loading="loading"
        :asset="isXs ? 'BTC' : undefined"
        :asset-padding="0.1"
      />
    </td>
    <td class="text-end px-4">
      <AmountDisplay
        fiat-currency="USD"
        show-currency="symbol"
        :value="usdSum"
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
