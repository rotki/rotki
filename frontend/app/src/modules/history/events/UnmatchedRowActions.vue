<script lang="ts">
export interface UnmatchedRowActionLabels {
  showInEventsTooltip: string;
  restore: string;
  restoreTooltip: string;
  findMatch: string;
  ignore: string;
  ignoreTooltip: string;
}

/**
 * An action that only some flows offer. Passing it is what renders the button, so its label can no
 * longer go missing the way a separate `show` flag plus an optional label allowed.
 */
export interface UnmatchedRowOptionalAction {
  label: string;
  tooltip: string;
  /** Renders the button filled, as the suggested resolution for the row. */
  emphasize?: boolean;
}
</script>

<script setup lang="ts">
const {
  labels,
  isPinned = false,
  showRestore = false,
  ignoreLoading = false,
  matchDisabled = false,
  markExternal,
  createCounterpart,
} = defineProps<{
  labels: UnmatchedRowActionLabels;
  isPinned?: boolean;
  showRestore?: boolean;
  ignoreLoading?: boolean;
  matchDisabled?: boolean;
  /** When given, renders the mark-external action. */
  markExternal?: UnmatchedRowOptionalAction;
  /** When given, renders the create-counterpart action. */
  createCounterpart?: UnmatchedRowOptionalAction;
}>();

const emit = defineEmits<{
  'show-in-events': [];
  'restore': [];
  'select': [];
  'ignore': [];
  'mark-external': [];
  'create-counterpart': [];
}>();
</script>

<template>
  <div class="flex items-center gap-2">
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
          @click="emit('show-in-events')"
        >
          <RuiIcon
            size="16"
            name="lu-external-link"
          />
        </RuiButton>
      </template>
      {{ labels.showInEventsTooltip }}
    </RuiTooltip>
    <template v-if="showRestore">
      <RuiTooltip
        :open-delay="400"
        :popper="{ placement: 'top' }"
      >
        <template #activator>
          <RuiButton
            size="sm"
            color="primary"
            :loading="ignoreLoading"
            @click="emit('restore')"
          >
            {{ labels.restore }}
          </RuiButton>
        </template>
        {{ labels.restoreTooltip }}
      </RuiTooltip>
    </template>
    <div
      v-else
      class="flex"
      :class="isPinned ? 'flex-wrap gap-1' : 'gap-2'"
    >
      <RuiButton
        size="sm"
        color="primary"
        :class="{ '!py-0.5': isPinned }"
        :disabled="matchDisabled"
        @click="emit('select')"
      >
        {{ labels.findMatch }}
      </RuiButton>
      <RuiTooltip
        :open-delay="400"
        :popper="{ placement: 'top' }"
      >
        <template #activator>
          <RuiButton
            size="sm"
            variant="outlined"
            :class="{ '!py-0.5': isPinned }"
            :loading="ignoreLoading"
            @click="emit('ignore')"
          >
            {{ labels.ignore }}
          </RuiButton>
        </template>
        {{ labels.ignoreTooltip }}
      </RuiTooltip>
      <RuiTooltip
        v-if="markExternal"
        :open-delay="400"
        :popper="{ placement: 'top' }"
      >
        <template #activator>
          <RuiButton
            size="sm"
            :variant="markExternal.emphasize ? 'default' : 'outlined'"
            color="warning"
            :class="{ '!py-0.5': isPinned }"
            :loading="ignoreLoading"
            @click="emit('mark-external')"
          >
            {{ markExternal.label }}
          </RuiButton>
        </template>
        {{ markExternal.tooltip }}
      </RuiTooltip>
      <RuiTooltip
        v-if="createCounterpart"
        :open-delay="400"
        :popper="{ placement: 'top' }"
      >
        <template #activator>
          <RuiButton
            size="sm"
            :variant="createCounterpart.emphasize ? 'default' : 'outlined'"
            color="info"
            :class="{ '!py-0.5': isPinned }"
            :loading="ignoreLoading"
            @click="emit('create-counterpart')"
          >
            {{ createCounterpart.label }}
          </RuiButton>
        </template>
        {{ createCounterpart.tooltip }}
      </RuiTooltip>
    </div>
  </div>
</template>
