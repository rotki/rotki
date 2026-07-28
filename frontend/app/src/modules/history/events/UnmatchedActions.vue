<script setup lang="ts">
import { UNMATCHED_ACTIONS, UNMATCHED_LAYOUTS, type UnmatchedAction, type UnmatchedLayout, type UnmatchedRowActionSpec, type UnmatchedRowConfirm } from '@/modules/history/events/unmatched-actions';
import UnmatchedConfirmStrip from '@/modules/history/events/UnmatchedConfirmStrip.vue';

// The action strip of a single unmatched row. The two arrangements differ only in how much
// room there is for labels, so they share one component: what a row may do is decided by the
// spec its surface hands down, and the layout only decides where the buttons go.
const { spec, layout, ignoreLoading = false } = defineProps<{
  spec: UnmatchedRowActionSpec;
  layout: UnmatchedLayout;
  ignoreLoading?: boolean;
}>();

const emit = defineEmits<{
  action: [action: UnmatchedAction];
}>();

const { t } = useI18n({ useScope: 'global' });

const pending = ref<UnmatchedAction>();
const menuOpen = ref<boolean>(false);

/**
 * The mockup's icon affordance: a bordered, rounded 30px box rather than a bare glyph.
 * Every button on the line shares that height so the row reads as one control strip.
 */
const ICON_BUTTON_CLASS = '!w-[30px] !h-[30px] !p-0 !rounded-lg shrink-0';

/**
 * Neutral actions take the divider colour; the outlined default is near-black and too
 * heavy next to the tinted buttons. `border-default` is a ui-library stylesheet class,
 * not a Tailwind utility here, so the shades it maps to are spelled out instead.
 */
const NEUTRAL_BORDER_CLASS = '!border-rui-grey-300 dark:!border-rui-grey-700 !text-rui-text-secondary';

const LABELLED_BUTTON_CLASS = '!h-[30px] !py-0';

const isCard = computed<boolean>(() => layout === UNMATCHED_LAYOUTS.CARD);

const pendingConfirm = computed<UnmatchedRowConfirm | undefined>(() => {
  const action = get(pending);
  return action ? spec.confirms?.[action] : undefined;
});

/**
 * At card width only one action can carry a label, so the row's suggested resolution takes
 * that slot: mark-external or create-counterpart when either is emphasized (an untracked or
 * unqueryable counterpart), otherwise find-match.
 */
const primary = computed<UnmatchedAction>(() => {
  if (spec.markExternal?.emphasize)
    return UNMATCHED_ACTIONS.MARK_EXTERNAL;
  if (spec.createCounterpart?.emphasize)
    return UNMATCHED_ACTIONS.CREATE_COUNTERPART;
  return UNMATCHED_ACTIONS.FIND_MATCH;
});

/** Card only: an action that lost the labelled slot falls back to an icon or the overflow. */
const showExternalIcon = computed<boolean>(() => !spec.showRestore && !!spec.markExternal && get(primary) !== UNMATCHED_ACTIONS.MARK_EXTERNAL);

const showFindMatchInMenu = computed<boolean>(() => !spec.showRestore && get(primary) !== UNMATCHED_ACTIONS.FIND_MATCH);

const showCounterpartInMenu = computed<boolean>(() => !spec.showRestore && !!spec.createCounterpart && get(primary) !== UNMATCHED_ACTIONS.CREATE_COUNTERPART);

/** Only worth an overflow when something is actually left to put in it. */
const hasMenu = computed<boolean>(() => get(showFindMatchInMenu) || get(showCounterpartInMenu));

/** Runs the action, unless it first wants a word with the user. */
function request(action: UnmatchedAction): void {
  if (spec.confirms?.[action]) {
    set(pending, action);
    return;
  }
  emit('action', action);
}

function accept(): void {
  const action = get(pending);
  set(pending, undefined);
  if (action)
    emit('action', action);
}
</script>

<template>
  <UnmatchedConfirmStrip
    v-if="pendingConfirm"
    :confirm="pendingConfirm"
    :loading="ignoreLoading"
    @cancel="pending = undefined"
    @confirm="accept()"
  />

  <!-- card: one labelled primary, then the rest of the line as icons -->
  <div
    v-else-if="isCard"
    class="flex items-center gap-1"
  >
    <RuiButton
      v-if="spec.showRestore"
      size="sm"
      color="primary"
      :class="LABELLED_BUTTON_CLASS"
      :loading="ignoreLoading"
      data-testid="unmatched-action-restore"
      @click="request(UNMATCHED_ACTIONS.RESTORE)"
    >
      {{ spec.labels.restore }}
    </RuiButton>

    <template v-else>
      <RuiButton
        v-if="primary === UNMATCHED_ACTIONS.FIND_MATCH"
        size="sm"
        color="primary"
        :class="LABELLED_BUTTON_CLASS"
        :disabled="spec.matchDisabled"
        data-testid="unmatched-action-primary"
        @click="request(UNMATCHED_ACTIONS.FIND_MATCH)"
      >
        {{ spec.labels.findMatch }}
      </RuiButton>
      <RuiButton
        v-else-if="primary === UNMATCHED_ACTIONS.MARK_EXTERNAL"
        size="sm"
        color="warning"
        :class="LABELLED_BUTTON_CLASS"
        :loading="ignoreLoading"
        data-testid="unmatched-action-primary"
        @click="request(UNMATCHED_ACTIONS.MARK_EXTERNAL)"
      >
        {{ spec.markExternal?.label }}
      </RuiButton>
      <RuiButton
        v-else
        size="sm"
        color="info"
        :class="LABELLED_BUTTON_CLASS"
        :loading="ignoreLoading"
        data-testid="unmatched-action-primary"
        @click="request(UNMATCHED_ACTIONS.CREATE_COUNTERPART)"
      >
        {{ spec.createCounterpart?.label }}
      </RuiButton>
    </template>

    <div class="ml-auto flex items-center gap-1">
      <!-- the jump to history stays on the line: it is how a row gets inspected, not a rare action -->
      <RuiTooltip
        :open-delay="400"
        :popper="{ placement: 'top' }"
      >
        <template #activator>
          <RuiButton
            size="sm"
            variant="outlined"
            icon
            color="primary"
            :class="ICON_BUTTON_CLASS"
            :aria-label="spec.labels.showInEventsTooltip"
            data-testid="unmatched-action-show-in-events"
            @click="request(UNMATCHED_ACTIONS.SHOW_IN_EVENTS)"
          >
            <RuiIcon
              size="16"
              name="lu-external-link"
            />
          </RuiButton>
        </template>
        {{ spec.labels.showInEventsTooltip }}
      </RuiTooltip>

      <RuiTooltip
        v-if="!spec.showRestore"
        :open-delay="400"
        :popper="{ placement: 'top' }"
      >
        <template #activator>
          <RuiButton
            size="sm"
            variant="outlined"
            icon
            :class="[ICON_BUTTON_CLASS, NEUTRAL_BORDER_CLASS]"
            :loading="ignoreLoading"
            :aria-label="spec.labels.ignore"
            data-testid="unmatched-action-ignore"
            @click="request(UNMATCHED_ACTIONS.IGNORE)"
          >
            <RuiIcon
              size="16"
              name="lu-circle-slash"
            />
          </RuiButton>
        </template>
        {{ spec.labels.ignoreTooltip }}
      </RuiTooltip>

      <RuiTooltip
        v-if="showExternalIcon"
        :open-delay="400"
        :popper="{ placement: 'top' }"
      >
        <template #activator>
          <RuiButton
            size="sm"
            variant="outlined"
            icon
            color="warning"
            :class="ICON_BUTTON_CLASS"
            :loading="ignoreLoading"
            :aria-label="spec.markExternal?.label"
            data-testid="unmatched-action-mark-external"
            @click="request(UNMATCHED_ACTIONS.MARK_EXTERNAL)"
          >
            <RuiIcon
              size="16"
              name="lu-square-arrow-out-up-right"
            />
          </RuiButton>
        </template>
        {{ spec.markExternal?.tooltip }}
      </RuiTooltip>

      <RuiMenu
        v-if="hasMenu"
        v-model="menuOpen"
        :popper="{ placement: 'bottom-end' }"
        close-on-content-click
      >
        <template #activator="{ attrs }">
          <RuiButton
            size="sm"
            variant="outlined"
            icon
            :class="[ICON_BUTTON_CLASS, NEUTRAL_BORDER_CLASS]"
            :aria-label="t('common.actions.more')"
            data-testid="unmatched-action-overflow"
            v-bind="attrs"
          >
            <RuiIcon
              size="16"
              name="lu-ellipsis"
            />
          </RuiButton>
        </template>

        <RuiButton
          v-if="showFindMatchInMenu"
          variant="list"
          :disabled="spec.matchDisabled"
          data-testid="unmatched-action-find-match"
          @click="request(UNMATCHED_ACTIONS.FIND_MATCH)"
        >
          <template #prepend>
            <RuiIcon
              size="16"
              name="lu-search"
            />
          </template>
          {{ spec.labels.findMatchAnyway }}
        </RuiButton>

        <RuiButton
          v-if="showCounterpartInMenu"
          variant="list"
          :loading="ignoreLoading"
          data-testid="unmatched-action-create-counterpart"
          @click="request(UNMATCHED_ACTIONS.CREATE_COUNTERPART)"
        >
          <template #prepend>
            <RuiIcon
              size="16"
              name="lu-copy-plus"
            />
          </template>
          {{ spec.createCounterpart?.label }}
        </RuiButton>
      </RuiMenu>
    </div>
  </div>

  <!-- row: dialog width, so every action can carry its label -->
  <div
    v-else
    class="flex items-center gap-2"
  >
    <RuiTooltip
      :open-delay="400"
      :popper="{ placement: 'top' }"
    >
      <template #activator>
        <RuiButton
          size="sm"
          variant="outlined"
          icon
          color="primary"
          class="!px-2 h-[30px]"
          :aria-label="spec.labels.showInEventsTooltip"
          data-testid="unmatched-action-show-in-events"
          @click="request(UNMATCHED_ACTIONS.SHOW_IN_EVENTS)"
        >
          <RuiIcon
            size="16"
            name="lu-external-link"
          />
        </RuiButton>
      </template>
      {{ spec.labels.showInEventsTooltip }}
    </RuiTooltip>

    <RuiTooltip
      v-if="spec.showRestore"
      :open-delay="400"
      :popper="{ placement: 'top' }"
    >
      <template #activator>
        <RuiButton
          size="sm"
          color="primary"
          :loading="ignoreLoading"
          data-testid="unmatched-action-restore"
          @click="request(UNMATCHED_ACTIONS.RESTORE)"
        >
          {{ spec.labels.restore }}
        </RuiButton>
      </template>
      {{ spec.labels.restoreTooltip }}
    </RuiTooltip>

    <div
      v-else
      class="flex gap-2"
    >
      <RuiButton
        size="sm"
        color="primary"
        :disabled="spec.matchDisabled"
        data-testid="unmatched-action-find-match"
        @click="request(UNMATCHED_ACTIONS.FIND_MATCH)"
      >
        {{ spec.labels.findMatch }}
      </RuiButton>
      <RuiTooltip
        :open-delay="400"
        :popper="{ placement: 'top' }"
      >
        <template #activator>
          <RuiButton
            size="sm"
            variant="outlined"
            :loading="ignoreLoading"
            data-testid="unmatched-action-ignore"
            @click="request(UNMATCHED_ACTIONS.IGNORE)"
          >
            {{ spec.labels.ignore }}
          </RuiButton>
        </template>
        {{ spec.labels.ignoreTooltip }}
      </RuiTooltip>
      <RuiTooltip
        v-if="spec.markExternal"
        :open-delay="400"
        :popper="{ placement: 'top' }"
      >
        <template #activator>
          <RuiButton
            size="sm"
            :variant="spec.markExternal.emphasize ? 'default' : 'outlined'"
            color="warning"
            :loading="ignoreLoading"
            data-testid="unmatched-action-mark-external"
            @click="request(UNMATCHED_ACTIONS.MARK_EXTERNAL)"
          >
            {{ spec.markExternal.label }}
          </RuiButton>
        </template>
        {{ spec.markExternal.tooltip }}
      </RuiTooltip>
      <RuiTooltip
        v-if="spec.createCounterpart"
        :open-delay="400"
        :popper="{ placement: 'top' }"
      >
        <template #activator>
          <RuiButton
            size="sm"
            :variant="spec.createCounterpart.emphasize ? 'default' : 'outlined'"
            color="info"
            :loading="ignoreLoading"
            data-testid="unmatched-action-create-counterpart"
            @click="request(UNMATCHED_ACTIONS.CREATE_COUNTERPART)"
          >
            {{ spec.createCounterpart.label }}
          </RuiButton>
        </template>
        {{ spec.createCounterpart.tooltip }}
      </RuiTooltip>
    </div>
  </div>
</template>
