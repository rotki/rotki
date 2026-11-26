<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import { RuiNavigationDrawer, RuiTab, RuiTabs } from '@rotki/ui-library';
import { isDefined } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { computed, useTemplateRef, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { getAccountLabel, isXpubAccount } from '@/modules/accounts/account-utils';
import AccountGroupDetailsTable from '@/modules/accounts/AccountGroupDetailsTable.vue';
import { AccountDetailsView } from '@/modules/accounts/details/account-details-views';
import AccountDetailsAssets from '@/modules/accounts/details/AccountDetailsAssets.vue';
import AccountDetailsChains from '@/modules/accounts/details/AccountDetailsChains.vue';
import AccountDetailsHeader from '@/modules/accounts/details/AccountDetailsHeader.vue';
import { useAccountDetailsTarget } from '@/modules/accounts/details/use-account-details-target';
import { useDrawerDismiss } from '@/modules/accounts/details/use-drawer-dismiss';
import { useDrawerFocus } from '@/modules/accounts/details/use-drawer-focus';
import { useDrawerOutsideClose } from '@/modules/accounts/details/use-drawer-outside-close';
import { provideTableScroller } from '@/modules/core/table/use-table-row-window';

const selectedAssets = defineModel<string[] | undefined>('selectedAssets', { required: true });

/** Chains switched off per group, shared with the table row so both show the same scope. */
const chainExclusionFilter = defineModel<Record<string, string[]>>('chainExclusionFilter', { required: true });

const { category, selectionMode, visibleTags } = defineProps<{
  category: string;
  visibleTags: string[];
  selectionMode: boolean;
}>();

const emit = defineEmits<{
  edit: [account: AccountManageState];
}>();

defineSlots<{
  /**
   * Actions on the selected assets, shown above the list while selection mode is on.
   *
   * @remarks
   * Assets are picked in the drawer, so the actions on them have to be in it too: the drawer closes
   * on any click outside it, which made the page's own selection bar unusable while it was open.
   */
  'selection-actions'?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const detailsTable = useTemplateRef<ComponentExposed<typeof AccountGroupDetailsTable>>('detailsTable');
const header = useTemplateRef<ComponentExposed<typeof AccountDetailsHeader>>('header');
const scroller = useTemplateRef<HTMLDivElement>('scroller');
const content = useTemplateRef<HTMLDivElement>('content');

provideTableScroller(scroller);

const {
  chains,
  chainsFiltered,
  currentView,
  emptyAddressCount,
  groupId,
  isOpen,
  onClosed,
  openAccount,
  ready,
  shownGroup,
  tabIndex,
  views,
} = useAccountDetailsTarget({
  category: () => category,
  chainExclusionFilter,
});

const { onKeydown } = useDrawerDismiss({
  close: () => set(isOpen, false),
  open: isOpen,
});

const viewLabels = computed<Record<AccountDetailsView, string>>(() => ({
  [AccountDetailsView.ACCOUNTS]: t('account_balances.accounts'),
  [AccountDetailsView.ADDRESSES]: t('account_balances.addresses'),
  [AccountDetailsView.ASSETS]: t('common.assets'),
  [AccountDetailsView.CHAINS]: t('account_balances.per_chain'),
}));

async function refresh(): Promise<void> {
  if (isDefined(detailsTable))
    await get(detailsTable).refresh();
}

useDrawerFocus(isOpen, () => get(header)?.focusClose(), content);

useDrawerOutsideClose({
  close: () => set(isOpen, false),
  open: isOpen,
  target: content,
});

/** Another account starts fresh: its lists are keyed on it, and the scroll goes back to the top. */
watch(groupId, () => {
  const element = get(scroller);
  if (element)
    element.scrollTop = 0;
});

defineExpose({
  isOpen,
  open: openAccount,
  refresh,
});
</script>

<template>
  <RuiNavigationDrawer
    v-model="isOpen"
    below-app-bar
    width="min(860px, 100vw)"
    temporary
    stateless
    position="right"
    :aria-label="shownGroup ? t('account_balances.details_of', { account: getAccountLabel(shownGroup) }) : t('common.details')"
    :class-names="{ content: 'flex flex-col' }"
    data-testid="account-details-drawer"
    @closed="onClosed()"
  >
    <div
      v-if="shownGroup && groupId"
      ref="content"
      class="contents"
      data-testid="account-details-content"
      @keydown="onKeydown($event)"
    >
      <AccountDetailsHeader
        ref="header"
        v-model:chain-filter="chainExclusionFilter"
        :group="shownGroup"
        @close="isOpen = false"
      />

      <RuiTabs
        v-if="views.length > 1"
        v-model="tabIndex"
        color="primary"
        class="px-4 border-b border-default"
      >
        <RuiTab
          v-for="item in views"
          :key="item"
          :data-testid="`account-details-tab-${item}`"
        >
          {{ viewLabels[item] }}
        </RuiTab>
      </RuiTabs>

      <div
        v-if="selectionMode && $slots['selection-actions']"
        class="flex px-4 py-2 border-b border-default"
        data-testid="account-details-selection-actions"
      >
        <slot name="selection-actions" />
      </div>

      <div
        ref="scroller"
        class="flex-1 overflow-y-auto p-4"
      >
        <template v-if="ready">
          <AccountDetailsAssets
            v-if="currentView === AccountDetailsView.ASSETS"
            :key="groupId"
            v-model:selected="selectedAssets"
            :group-id="groupId"
            :chains="chains"
            :selection-mode="selectionMode"
            searchable
          />
          <AccountDetailsChains
            v-else-if="currentView === AccountDetailsView.CHAINS"
            v-model:selected="selectedAssets"
            :group-id="groupId"
            :chains="chains"
            :filtered="chainsFiltered"
            :selection-mode="selectionMode"
          />
          <AccountGroupDetailsTable
            v-else
            ref="detailsTable"
            :key="groupId"
            v-model:selected="selectedAssets"
            :group-id="groupId"
            :chains="chains"
            :tags="visibleTags"
            :category="category"
            :selection-mode="selectionMode"
            :group="isXpubAccount(shownGroup) ? 'xpub' : undefined"
            :empty-count="emptyAddressCount"
            @edit="emit('edit', $event)"
          />
        </template>
      </div>
    </div>
  </RuiNavigationDrawer>
</template>
