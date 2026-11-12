<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { ExchangeAccountOption } from '@/modules/balances/exchanges/use-exchange-account-selection';
import ExchangeAccountOptionRow from '@/modules/balances/exchanges/ExchangeAccountOptionRow.vue';

const modelValue = defineModel<string | undefined>({ required: true });

const { accounts, total } = defineProps<{
  accounts: ExchangeAccountOption[];
  /** The whole exchange's total, the same figure its card shows. */
  total: BigNumber;
}>();

/** Past this many accounts a list is easier to search than to scan, so the menu offers a filter. */
const SEARCH_FROM = 7;

const { t } = useI18n({ useScope: 'global' });

const open = ref<boolean>(false);
const filter = ref<string>('');

const picked = computed<ExchangeAccountOption | undefined>(() =>
  accounts.find(account => account.identifier === get(modelValue)));

/** The whole exchange as an option of its own; it has no share, being the whole. */
const allAccounts = computed<ExchangeAccountOption>(() => ({
  identifier: 'all',
  loaded: true,
  name: t('exchange_balances.accounts.all'),
  share: '',
  value: total,
}));

const searchable = computed<boolean>(() => accounts.length >= SEARCH_FROM);

const shown = computed<ExchangeAccountOption[]>(() => {
  const needle = get(filter).trim().toLocaleLowerCase();
  return needle ? accounts.filter(account => account.name.toLocaleLowerCase().includes(needle)) : accounts;
});

function pick(identifier: string | undefined): void {
  set(modelValue, identifier);
  set(open, false);
}

/** Enter in the filter picks the first match, as the currency menu does. */
function pickFirstMatch(): void {
  const [first] = get(shown);
  if (first)
    pick(first.identifier);
}

watch(open, (isOpen) => {
  if (!isOpen)
    set(filter, '');
});
</script>

<template>
  <RuiMenu
    v-model="open"
    :class-names="{ menu: 'w-96 max-w-[calc(100vw-2rem)]' }"
    :options="{ placement: 'bottom-start' }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="outlined"
        class="max-w-72"
        data-testid="exchange-account-picker"
        v-bind="attrs"
      >
        <template #prepend>
          <RuiIcon
            :name="picked?.error ? 'lu-triangle-alert' : 'lu-key-round'"
            :color="picked?.error ? 'warning' : undefined"
            size="16"
          />
        </template>
        <span class="truncate">{{ picked?.name ?? t('exchange_balances.accounts.all') }}</span>
        <template #append>
          <RuiIcon
            name="lu-chevron-down"
            size="16"
          />
        </template>
      </RuiButton>
    </template>
    <div
      v-if="searchable"
      class="border-b border-rui-divider p-3"
    >
      <RuiTextField
        v-model="filter"
        dense
        autofocus
        details="hidden"
        clearable
        color="primary"
        :label="t('common.actions.filter')"
        label-placement="hidden"
        :placeholder="t('exchange_balances.accounts.search')"
        prepend-icon="lu-search"
        data-testid="exchange-account-search"
        @keyup.enter="pickFirstMatch()"
      />
    </div>
    <div
      role="group"
      :aria-label="t('exchange_balances.accounts.label')"
    >
      <template v-if="!filter">
        <div class="py-1">
          <ExchangeAccountOptionRow
            class="font-medium"
            :account="allAccounts"
            :selected="!picked"
            @pick="pick(undefined)"
          >
            <template #prepend>
              <RuiIcon
                name="lu-coins-exchange"
                size="16"
                class="shrink-0 text-rui-text-secondary"
              />
            </template>
          </ExchangeAccountOptionRow>
        </div>
        <RuiDivider />
      </template>
      <div
        class="px-4 pt-2 pb-1 text-caption uppercase tracking-wide text-rui-text-secondary"
        data-testid="exchange-account-section"
      >
        {{ t('exchange_balances.accounts.section', { count: shown.length }) }}
      </div>
      <div class="max-h-88 overflow-auto pb-1">
        <ExchangeAccountOptionRow
          v-for="account in shown"
          :key="account.identifier"
          :account="account"
          :selected="picked?.identifier === account.identifier"
          @pick="pick($event)"
        />
        <div
          v-if="shown.length === 0"
          class="px-4 py-3 text-sm text-rui-text-secondary"
          data-testid="exchange-account-no-match"
        >
          {{ t('exchange_balances.accounts.no_match') }}
        </div>
      </div>
    </div>
  </RuiMenu>
</template>
