<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';

const open = defineModel<boolean>({ default: false });

const { badge = false, checking = false, count } = defineProps<{
  /** how many categories are asking for something */
  count: number;
  checking?: boolean;
  /**
   * Shows the count on the trigger.
   *
   * @remarks
   * Only the global trigger carries it: two badges counting the same rows are how the numbers
   * start to disagree, so a scoped view shows the state without the number.
   */
  badge?: boolean;
}>();

defineSlots<{
  /** the panel the trigger opens, usually an `ActionCenterList` */
  default: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

/**
 * Names the trigger's state, and doubles as its accessible name.
 *
 * @remarks
 * A badge reaches a screen reader as a bare number, so the count is spelled out here.
 */
const tooltip = computed<string>(() => {
  if (count > 0)
    return t('action_center.subtitle', { count }, count);
  return checking ? t('action_center.button_checking') : t('action_center.button_clear');
});

/**
 * The trigger's icon, which never spins.
 *
 * @remarks
 * The task dock and the sync indicator already carry the motion, so a third spinner here would only
 * add noise.
 */
const icon = computed<RuiIcons>(() => {
  if (count > 0)
    return 'lu-triangle-alert';
  return checking ? 'lu-circle-dashed' : 'lu-circle-check';
});
</script>

<template>
  <RuiMenu
    v-model="open"
    :options="{ placement: 'bottom-end' }"
    :class-names="{ menu: 'w-[36rem] max-w-[90vw]' }"
  >
    <template #activator="{ attrs }">
      <RuiTooltip
        :options="{ placement: 'bottom' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            size="lg"
            :class="count > 0 ? '!text-rui-warning' : '!text-rui-text-secondary'"
            data-testid="actions-center-button"
            :aria-label="tooltip"
            v-bind="attrs"
          >
            <RuiBadge
              :model-value="badge && count > 0"
              :text="count.toString()"
              color="warning"
              placement="top"
              size="sm"
              offset-y="4"
              offset-x="-4"
              data-testid="actions-center-button-badge"
            >
              <RuiIcon :name="icon" />
            </RuiBadge>
          </RuiButton>
        </template>
        {{ tooltip }}
      </RuiTooltip>
    </template>

    <slot />
  </RuiMenu>
</template>
