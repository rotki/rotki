<script setup lang="ts">
const open = defineModel<boolean>({ default: false });

const { checking = false, count } = defineProps<{
  /** how many categories are asking for something: the badge, and whether there is one */
  count: number;
  checking?: boolean;
}>();

defineSlots<{
  /** the panel the trigger opens, usually an `ActionCenterList` */
  default: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const tooltip = computed<string>(() => checking
  ? t('action_center.button_checking')
  : t('action_center.button_clear'));
</script>

<template>
  <RuiMenu
    v-model="open"
    :options="{ placement: 'bottom-end' }"
    :class-names="{ menu: 'w-[36rem] max-w-[90vw]' }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        v-if="count > 0"
        size="lg"
        variant="outlined"
        color="warning"
        class="!rounded-full !bg-rui-warning/10 [&>span]:!hidden lg:[&>span]:!inline"
        data-testid="actions-center-button"
        v-bind="attrs"
      >
        <template #prepend>
          <RuiIcon
            name="lu-triangle-alert"
            size="18"
          />
        </template>

        {{ t('action_center.button') }}

        <template #append>
          <span
            class="ml-1 min-w-5 px-1.5 rounded-full bg-rui-warning text-white text-caption font-medium leading-5 text-center"
            data-testid="actions-center-button-count"
          >
            {{ count }}
          </span>
        </template>
      </RuiButton>

      <RuiTooltip
        v-else
        :options="{ placement: 'bottom' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            size="lg"
            class="!text-rui-text-secondary"
            data-testid="actions-center-button"
            :aria-label="tooltip"
            v-bind="attrs"
          >
            <!-- static icon on purpose: the sync panel and the pending-task list already
                 carry the motion, a third spinner here would only add noise -->
            <RuiIcon :name="checking ? 'lu-circle-dashed' : 'lu-circle-check'" />
          </RuiButton>
        </template>
        {{ tooltip }}
      </RuiTooltip>
    </template>

    <slot />
  </RuiMenu>
</template>
