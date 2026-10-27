<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { BlockchainAccountGroupWithBalance } from '@/modules/accounts/blockchain-accounts';
import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import type { LocationQuery } from '@/modules/core/table/route';
import { startPromise } from '@shared/utils';
import { type AccountGroupId, getAccountLabel, getGroupId } from '@/modules/accounts/account-utils';
import AccountGroupDetailsTable from '@/modules/accounts/AccountGroupDetailsTable.vue';
import { AccountDetailsView, accountDetailsViews } from '@/modules/accounts/details/account-details-views';
import AccountDetailsAssets from '@/modules/accounts/details/AccountDetailsAssets.vue';
import AccountDetailsChainSection from '@/modules/accounts/details/AccountDetailsChainSection.vue';
import AccountDetailsHeader from '@/modules/accounts/details/AccountDetailsHeader.vue';
import { useAccountDetailsRoute } from '@/modules/accounts/details/use-account-details-route';
import { useDrawerDismiss } from '@/modules/accounts/details/use-drawer-dismiss';
import { useDrawerFocus } from '@/modules/accounts/details/use-drawer-focus';
import { useDrawerOutsideClose } from '@/modules/accounts/details/use-drawer-outside-close';
import { useDrawerPresence } from '@/modules/accounts/details/use-drawer-presence';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
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

const detailsTableQuery = ref<LocationQuery>({});
const detailsTable = useTemplateRef<ComponentExposed<typeof AccountGroupDetailsTable>>('detailsTable');
const header = useTemplateRef<ComponentExposed<typeof AccountDetailsHeader>>('header');
const scroller = useTemplateRef<HTMLDivElement>('scroller');
const content = useTemplateRef<HTMLDivElement>('content');

provideTableScroller(scroller);

const { isChainSettled } = useBlockchainAccountsStore();

const { accountId, close, discard, open, setView, view } = useAccountDetailsRoute();
const { getAccountsByCategory } = useBlockchainAccountData();
const { chainIds } = useAccountCategoryHelper(() => category);
const groups = getAccountsByCategory(() => category);

const group = computed<BlockchainAccountGroupWithBalance | undefined>(() => {
  const id = get(accountId);
  return id ? get(groups).find(item => getGroupId(item) === id) : undefined;
});

/** The account open and the tab the URL asks for, held together so neither changes while the drawer slides out. */
const opened = computed<{ group: BlockchainAccountGroupWithBalance; view?: AccountDetailsView } | undefined>(() => {
  const current = get(group);
  return current ? { group: current, view: get(view) } : undefined;
});

const { onClosed, ready, shown } = useDrawerPresence(opened);

const shownGroup = computed<BlockchainAccountGroupWithBalance | undefined>(() => get(shown)?.group);

/** Every chain of the category has finished its accounts read, so a missing account is really gone. */
const accountsSettled = computed<boolean>(() => {
  const ids = get(chainIds);
  return ids.length > 0 && ids.every(chain => isChainSettled(chain));
});

const groupId = computed<AccountGroupId | undefined>(() => {
  const current = get(shownGroup);
  return current ? getGroupId(current) : undefined;
});

const chains = computed<string[]>(() => {
  const current = get(shownGroup);
  if (!current)
    return [];

  const excluded = get(chainExclusionFilter)[getGroupId(current)] ?? [];
  return current.chains.filter(chain => !excluded.includes(chain));
});

const views = computed<AccountDetailsView[]>(() => {
  const current = get(shownGroup);
  return current ? accountDetailsViews(current) : [AccountDetailsView.ASSETS];
});

const currentView = computed<AccountDetailsView>(() => {
  const requested = get(shown)?.view;
  return requested && get(views).includes(requested) ? requested : AccountDetailsView.ASSETS;
});

const tabIndex = computed<number>({
  get: () => get(views).indexOf(get(currentView)),
  set: (index: number) => {
    const next = get(views)[index];
    if (next)
      startPromise(setView(next));
  },
});

const isOpen = computed<boolean>({
  get: () => isDefined(group),
  set: (value: boolean) => {
    if (!value)
      startPromise(close());
  },
});

const { onKeydown } = useDrawerDismiss({
  close: () => set(isOpen, false),
  open: isOpen,
});

function viewLabel(item: AccountDetailsView): string {
  if (item === AccountDetailsView.CHAINS)
    return t('account_balances.per_chain');
  if (item === AccountDetailsView.ADDRESSES)
    return t('account_balances.addresses');
  if (item === AccountDetailsView.ACCOUNTS)
    return t('account_balances.accounts');
  return t('common.assets');
}

/** A push while nothing shows, so Back closes it; a replace when it only switches the account. */
async function openAccount(id: string): Promise<void> {
  await open(id, isDefined(group) ? 'replace' : 'push');
}

async function refresh(): Promise<void> {
  if (isDefined(detailsTable))
    await get(detailsTable).refresh();
}

/** A key that names no account of this category (a stale link, a removed account) is dropped. */
function discardUnknownAccount(): void {
  if (get(accountId) && get(accountsSettled) && !isDefined(group))
    startPromise(discard());
}

useDrawerFocus(isOpen, () => get(header)?.focusClose(), content);

useDrawerOutsideClose({
  close: () => set(isOpen, false),
  open: isOpen,
  target: content,
});

/** Another account starts fresh: its lists are keyed on it, and the scroll goes back to the top. */
watch(groupId, () => {
  set(detailsTableQuery, {});
  const element = get(scroller);
  if (element)
    element.scrollTop = 0;
});

watchImmediate([accountId, accountsSettled, group], discardUnknownAccount);

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
          {{ viewLabel(item) }}
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
          <div
            v-else-if="currentView === AccountDetailsView.CHAINS"
            class="flex flex-col gap-6"
          >
            <AccountDetailsChainSection
              v-for="chain in chains"
              :key="`${groupId}:${chain}`"
              v-model:selected="selectedAssets"
              :chain="chain"
              :group-id="groupId"
              :selection-mode="selectionMode"
            />
          </div>
          <AccountGroupDetailsTable
            v-else
            ref="detailsTable"
            v-model:query="detailsTableQuery"
            v-model:selected="selectedAssets"
            :group-id="groupId"
            :chains="chains"
            :tags="visibleTags"
            :category="category"
            :selection-mode="selectionMode"
            @edit="emit('edit', $event)"
          />
        </template>
      </div>
    </div>
  </RuiNavigationDrawer>
</template>
