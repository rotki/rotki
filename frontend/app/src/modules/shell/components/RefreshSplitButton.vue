<script setup lang="ts">
import { createReusableTemplate } from '@vueuse/core';

/**
 * A refresh button with a chevron that opens a menu of narrower refresh actions.
 *
 * @remarks
 * The default slot is the menu body. It receives `close`, which an action calls before it starts so
 * the menu does not stay open over the work it began, and `isOpen`, for a body that should only
 * render while it is visible.
 */
const {
  testId,
  menuLabel,
  tooltip,
  loading = false,
  disabled = false,
  menuDisabled = false,
  hideMenu = false,
} = defineProps<{
  /** Test id of the main button; the menu trigger gets the same id with a `-menu` suffix. */
  testId: string;
  /** Accessible name of the icon-only menu trigger. */
  menuLabel: string;
  /** Shown on hover over the main button; no tooltip when absent. */
  tooltip?: string;
  loading?: boolean;
  disabled?: boolean;
  menuDisabled?: boolean;
  hideMenu?: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

defineSlots<{
  default: (props: { close: () => void; isOpen: boolean }) => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const menuOpen = ref<boolean>(false);

/** The main button, rendered bare when there is no tooltip so the group keeps buttons as direct children. */
const [DefineRefreshButton, ReuseRefreshButton] = createReusableTemplate();

function close(): void {
  set(menuOpen, false);
}
</script>

<template>
  <DefineRefreshButton>
    <RuiButton
      :data-testid="testId"
      :disabled="disabled"
      :loading="loading"
      @click="emit('refresh')"
    >
      <template #prepend>
        <RuiIcon name="lu-refresh-ccw" />
      </template>
      {{ t('common.refresh') }}
    </RuiButton>
  </DefineRefreshButton>
  <RuiButtonGroup
    variant="outlined"
    color="primary"
  >
    <RuiTooltip
      v-if="tooltip"
      :open-delay="400"
      :class-names="{ root: 'flex' }"
    >
      <template #activator>
        <ReuseRefreshButton />
      </template>
      {{ tooltip }}
    </RuiTooltip>
    <ReuseRefreshButton v-else />
    <RuiMenu
      v-if="!hideMenu"
      v-model="menuOpen"
      :options="{ placement: 'bottom-end' }"
      :class-names="{ root: 'flex' }"
    >
      <template #activator="{ attrs }">
        <RuiButton
          v-bind="{
            ...attrs,
            'data-testid': `${testId}-menu`,
          }"
          color="primary"
          variant="outlined"
          class="px-2"
          :disabled="menuDisabled"
          :aria-label="menuLabel"
        >
          <RuiIcon name="lu-chevron-down" />
        </RuiButton>
      </template>

      <slot
        :close="close"
        :is-open="menuOpen"
      />
    </RuiMenu>
  </RuiButtonGroup>
</template>
