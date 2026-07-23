<script lang="ts">
export interface UnmatchedRowActionLabels {
  showInEventsTooltip: string;
  restore: string;
  restoreTooltip: string;
  findMatch: string;
  ignore: string;
  ignoreTooltip: string;
  markExternal?: string;
  markExternalTooltip?: string;
  createCounterpart?: string;
  createCounterpartTooltip?: string;
}
</script>

<script setup lang="ts">
const {
  labels,
  isPinned = false,
  showRestore = false,
  ignoreLoading = false,
  matchDisabled = false,
  showMarkExternal = false,
  emphasizeMarkExternal = false,
  showCreateCounterpart = false,
  emphasizeCreateCounterpart = false,
} = defineProps<{
  labels: UnmatchedRowActionLabels;
  isPinned?: boolean;
  showRestore?: boolean;
  ignoreLoading?: boolean;
  matchDisabled?: boolean;
  showMarkExternal?: boolean;
  /** Renders the mark-external button filled, as the suggested resolution for the row. */
  emphasizeMarkExternal?: boolean;
  showCreateCounterpart?: boolean;
  /** Renders the create-counterpart button filled, as the suggested resolution for the row. */
  emphasizeCreateCounterpart?: boolean;
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
        v-if="showMarkExternal"
        :open-delay="400"
        :popper="{ placement: 'top' }"
      >
        <template #activator>
          <RuiButton
            size="sm"
            :variant="emphasizeMarkExternal ? 'default' : 'outlined'"
            color="warning"
            :class="{ '!py-0.5': isPinned }"
            :loading="ignoreLoading"
            @click="emit('mark-external')"
          >
            {{ labels.markExternal }}
          </RuiButton>
        </template>
        {{ labels.markExternalTooltip }}
      </RuiTooltip>
      <RuiTooltip
        v-if="showCreateCounterpart"
        :open-delay="400"
        :popper="{ placement: 'top' }"
      >
        <template #activator>
          <RuiButton
            size="sm"
            :variant="emphasizeCreateCounterpart ? 'default' : 'outlined'"
            color="info"
            :class="{ '!py-0.5': isPinned }"
            :loading="ignoreLoading"
            @click="emit('create-counterpart')"
          >
            {{ labels.createCounterpart }}
          </RuiButton>
        </template>
        {{ labels.createCounterpartTooltip }}
      </RuiTooltip>
    </div>
  </div>
</template>
