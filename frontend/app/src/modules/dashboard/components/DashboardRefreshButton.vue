<script setup lang="ts">
import { type BalanceSource, RefreshSource } from '@/modules/balances/refresh/core/refresh-types';
import {
  DashboardExtraSource,
  type DashboardRefreshAction,
  DashboardRefreshKind,
} from '@/modules/dashboard/dashboard-refresh-action';

interface MenuItem {
  readonly action: DashboardRefreshAction;
  readonly label: string;
  readonly hint?: string;
}

const { busy = false, extraSources = [], sources = [] } = defineProps<{
  busy?: boolean;
  /** Connected sources, each offered as a refresh of its own. */
  sources?: BalanceSource[];
  /** Dashboard tables with a query of their own, offered after the sources. */
  extraSources?: DashboardExtraSource[];
}>();

const emit = defineEmits<{
  refresh: [action: DashboardRefreshAction];
}>();

const { t } = useI18n({ useScope: 'global' });

const open = ref<boolean>(false);
const anchor = useTemplateRef<HTMLElement>('anchor');

const modeItems = computed<MenuItem[]>(() => [
  {
    action: { kind: DashboardRefreshKind.BALANCES },
    hint: t('dashboard.refresh.balances_hint'),
    label: t('dashboard.refresh.balances'),
  },
  {
    action: { kind: DashboardRefreshKind.REDETECT },
    hint: t('dashboard.refresh.redetect_hint'),
    label: t('dashboard.refresh.redetect'),
  },
  {
    action: { kind: DashboardRefreshKind.PRICES },
    hint: t('dashboard.refresh.prices_only_hint'),
    label: t('dashboard.refresh.prices_only'),
  },
]);

const sourceItems = computed<MenuItem[]>(() => [
  ...sources.map((source): MenuItem => ({
    action: { kind: DashboardRefreshKind.SOURCE, source },
    label: sourceLabel(source),
  })),
  ...extraSources.map((source): MenuItem => ({
    action: { kind: DashboardRefreshKind.EXTRA_SOURCE, source },
    label: source === DashboardExtraSource.NFTS ? t('dashboard.refresh.source.nfts') : t('dashboard.refresh.source.pools'),
  })),
]);

function sourceLabel(source: BalanceSource): string {
  switch (source) {
    case RefreshSource.BLOCKCHAIN:
      return t('dashboard.refresh.source.blockchain');
    case RefreshSource.EXCHANGES:
      return t('dashboard.refresh.source.exchanges');
    case RefreshSource.BANKS:
      return t('dashboard.refresh.source.banks');
    case RefreshSource.MANUAL:
      return t('dashboard.refresh.source.manual');
  }
}

function testIdOf(action: DashboardRefreshAction): string {
  return action.kind === DashboardRefreshKind.SOURCE || action.kind === DashboardRefreshKind.EXTRA_SOURCE
    ? `dashboard-refresh-source-${action.source}`
    : `dashboard-refresh-${action.kind}`;
}

function choose(action: DashboardRefreshAction): void {
  set(open, false);
  emit('refresh', action);
}
</script>

<template>
  <div
    ref="anchor"
    class="inline-flex"
  >
    <RuiButtonGroup
      variant="outlined"
      color="primary"
      size="sm"
    >
      <RuiTooltip
        :options="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            class="!outline-0 rounded-r-none"
            variant="outlined"
            color="primary"
            size="sm"
            :loading="busy"
            :disabled="busy"
            data-testid="dashboard-refresh"
            @click="emit('refresh', { kind: DashboardRefreshKind.BALANCES })"
          >
            <template #prepend>
              <RuiIcon
                name="lu-refresh-ccw"
                size="16"
              />
            </template>
            {{ t('dashboard.refresh.button') }}
          </RuiButton>
        </template>
        {{ t('dashboard.refresh.tooltip') }}
      </RuiTooltip>
      <RuiMenu
        v-model="open"
        :anchor-el="anchor ?? undefined"
        :class-names="{ wrapper: 'h-full' }"
        :options="{ placement: 'bottom-start' }"
      >
        <template #activator="{ attrs }">
          <RuiButton
            class="!outline-0 !rounded-l-none !rounded-r"
            icon
            variant="outlined"
            color="primary"
            size="sm"
            :disabled="busy"
            :aria-label="t('dashboard.refresh.menu_tooltip')"
            data-testid="dashboard-refresh-menu"
            v-bind="attrs"
          >
            <RuiIcon
              name="lu-chevron-down"
              size="16"
            />
          </RuiButton>
        </template>
        <div class="py-1.5 w-80">
          <RuiButton
            v-for="item in modeItems"
            :key="item.action.kind"
            variant="list"
            class="!py-2"
            :data-testid="testIdOf(item.action)"
            @click="choose(item.action)"
          >
            <div class="flex flex-col items-start gap-0.5 text-left whitespace-normal">
              <span>{{ item.label }}</span>
              <span class="text-xs leading-4 font-normal text-rui-text-secondary">{{ item.hint }}</span>
            </div>
          </RuiButton>
          <template v-if="sourceItems.length > 0">
            <RuiDivider class="my-1.5" />
            <div class="px-3 pt-1 pb-0.5 text-xs font-medium uppercase tracking-wider text-rui-text-secondary">
              {{ t('dashboard.refresh.source.title') }}
            </div>
            <RuiButton
              v-for="item in sourceItems"
              :key="testIdOf(item.action)"
              variant="list"
              class="!py-2 !font-normal"
              :data-testid="testIdOf(item.action)"
              @click="choose(item.action)"
            >
              {{ item.label }}
            </RuiButton>
          </template>
        </div>
      </RuiMenu>
    </RuiButtonGroup>
  </div>
</template>
