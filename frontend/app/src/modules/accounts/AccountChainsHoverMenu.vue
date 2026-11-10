<script setup lang="ts">
import type { AccountChainState } from '@/modules/accounts/AccountChainsOverflow.vue';
import AccountSkipQueriesToggle from '@/modules/accounts/table/components/table/AccountSkipQueriesToggle.vue';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

interface HoverHandlers {
  onMouseover?: () => void;
  onMouseleave?: () => void;
}

const open = defineModel<boolean>('open', { default: false });

const { items, filterable, skipAddress } = defineProps<{
  /** The chains drawn as icons, one of which the menu describes. */
  items: AccountChainState[];
  /** Clicking an icon hides its chain from the row's total, which takes a second chain to leave a total. */
  filterable: boolean;
  /** The address a skip rule would name, on the rows the backend can match one against. */
  skipAddress?: string;
}>();

defineSlots<{
  /** The icons; each calls `point` with its chain and element when the pointer enters it. */
  default: (props: { point: (chain: string, element: HTMLElement) => void }) => any;
}>();

/** How long the pointer rests on an icon before the menu opens. */
const OPEN_DELAY = 300;

const { t } = useI18n({ useScope: 'global' });
const { getChainName } = useSupportedChains();

const pointedChain = ref<string>();
const anchor = shallowRef<HTMLElement>();

/** Set on the first `point`, from the activator slot, which is the only place they are handed out. */
let handlers: HoverHandlers = {};

const { start: startOpen, stop: stopOpen } = useTimeoutFn(() => handlers.onMouseover?.(), OPEN_DELAY, { immediate: false });

const item = computed<AccountChainState | undefined>(() => items.find(entry => entry.chain === get(pointedChain)));

const skipChains = computed<string[]>(() => {
  const chain = get(pointedChain);
  return chain === undefined ? [] : [chain];
});

/**
 * Moves the menu to the icon under the pointer, opening it once the pointer has rested there.
 *
 * @remarks
 * The menu's own hover handler would set up its popover the moment the pointer crosses an icon,
 * and a setup is kept until the row unmounts, so sweeping the pointer over a long table would
 * leave one behind for every row it passed. The rest is waited out here instead, and an open menu
 * only follows the pointer.
 */
function point(chain: string, element: HTMLElement, hover: HoverHandlers): void {
  handlers = hover;
  set(pointedChain, chain);
  set(anchor, element);
  if (get(open)) {
    hover.onMouseover?.();
    return;
  }
  startOpen();
}

function leave(hover: HoverHandlers): void {
  stopOpen();
  hover.onMouseleave?.();
}
</script>

<template>
  <RuiMenu
    v-model="open"
    open-on-hover
    lazy
    disable-auto-focus
    :close-delay="200"
    :anchor-el="anchor"
    :options="{ placement: 'bottom-start' }"
  >
    <template #activator="{ attrs }">
      <div
        class="flex flex-row-reverse items-center gap-1.5"
        data-testid="account-chain-icons"
        @mouseleave="leave(attrs)"
      >
        <slot :point="(chain: string, element: HTMLElement) => point(chain, element, attrs)" />
      </div>
    </template>

    <div
      v-if="item"
      class="py-1"
      :class="{ 'w-80': skipAddress !== undefined }"
      data-testid="account-chain-menu"
    >
      <div class="px-4 py-1.5 text-body-2 flex flex-col gap-1">
        <div
          v-if="item.skipped"
          data-testid="account-chain-skipped-tooltip"
        >
          {{ t('account_balances.skip_queries.chain_marker', { chain: getChainName(item.chain) }) }}
        </div>
        <template v-if="filterable">
          <i18n-t
            v-if="item.enabled"
            scope="global"
            keypath="account_balances.chain_filter.remove"
            tag="span"
          >
            <template #chain>
              <b>{{ getChainName(item.chain) }}</b>
            </template>
          </i18n-t>
          <i18n-t
            v-else
            scope="global"
            keypath="account_balances.chain_filter.add"
            tag="span"
          >
            <template #chain>
              <b>{{ getChainName(item.chain) }}</b>
            </template>
          </i18n-t>
        </template>
        <template v-else-if="!item.skipped">
          {{ getChainName(item.chain) }}
        </template>
      </div>
      <template v-if="skipAddress !== undefined">
        <RuiDivider class="my-1" />
        <AccountSkipQueriesToggle
          :address="skipAddress"
          :chains="skipChains"
        />
      </template>
    </div>
  </RuiMenu>
</template>
