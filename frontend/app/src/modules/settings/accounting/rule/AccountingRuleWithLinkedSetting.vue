<script setup lang="ts">
import type { AccountingRuleWithLinkedProperty } from '@/modules/settings/types/accounting';
import { useModelMirror } from '@/modules/core/form/use-model-mirror';
import { type LinkedPropertyState, toLinkedProperty, toLinkedPropertyState } from '@/modules/settings/accounting/rule/accounting-rule-form';
import { useAccountingRuleMappings } from '@/modules/settings/accounting/use-accounting-rule-mappings';
import SuccessDisplay from '@/modules/shell/components/display/SuccessDisplay.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const modelValue = defineModel<AccountingRuleWithLinkedProperty>({ required: true });

const { identifier, label, hint, learnMoreUrl } = defineProps<{
  identifier: string;
  label: string;
  hint: string;
  learnMoreUrl?: string;
}>();

const { t } = useI18n({ useScope: 'global' });

/**
 * The three controls, over a payload of two fields where the absence of one is what the checkbox
 * means. Mapped once here so that each control binds to plain state.
 */
const state = reactive<LinkedPropertyState>(toLinkedPropertyState(get(modelValue)));

useModelMirror<AccountingRuleWithLinkedProperty, LinkedPropertyState>({
  model: modelValue,
  state,
  toModel: toLinkedProperty,
  toState: toLinkedPropertyState,
});

const { accountingRuleLinkedMappingData } = useAccountingRuleMappings();

const linkableSettingOptions = accountingRuleLinkedMappingData(() => identifier);

/**
 * Whether the rule follows a linked setting.
 *
 * @remarks
 * Not a plain wrapper over the payload: ticking has to choose the setting the select below opens on,
 * and unticking has to let it go. The options arrive over the api, so a rule opened before they land
 * has nothing to link to, and the tick is refused outright rather than taken and undone, which would
 * flash the select open on its way back out.
 */
const linked = computed<boolean>({
  get: () => state.linked,
  set: (value: boolean) => {
    const first = get(linkableSettingOptions)[0]?.identifier;
    if (value && !first)
      return;

    state.linked = value;
    state.linkedSetting = value && first ? first : '';
  },
});

const linkedPropertyValue = computed<boolean | null>(() => {
  if (!state.linked || !state.linkedSetting)
    return null;

  const item = get(linkableSettingOptions).find(item => item.identifier === state.linkedSetting);

  if (!item)
    return null;

  return get(item.state);
});

/** A linked rule takes its value from the setting, so the disabled switch shows that value rather than the rule's own. */
const shownValue = computed<boolean>(() => {
  if (!state.linked)
    return state.value;
  return get(linkedPropertyValue) ?? false;
});

const elemID = computed<string>(() => `${identifier}-switch`);
</script>

<template>
  <div class="flex flex-col gap-1 px-4 py-3">
    <div class="flex items-start gap-4">
      <label
        :for="elemID"
        class="flex-1 cursor-pointer"
      >
        <span class="block text-sm font-medium text-rui-text">
          {{ label }}
        </span>
        <span class="block text-xs text-rui-text-secondary mt-0.5">
          {{ hint }}
          <ExternalLink
            v-if="learnMoreUrl"
            :url="learnMoreUrl"
            color="primary"
            class="text-xs"
            :text="t('accounting_settings.rule.learn_more')"
            @click.stop
          />
        </span>
      </label>
      <RuiSwitch
        :id="elemID"
        :model-value="shownValue"
        color="primary"
        hide-details
        :disabled="state.linked"
        @update:model-value="state.value = $event"
      />
    </div>
    <RuiCheckbox
      v-model="linked"
      size="sm"
      color="primary"
      hide-details
    >
      <span class="text-xs text-rui-text-secondary">
        {{ t('accounting_settings.rule.overwrite_by_setting') }}
      </span>
    </RuiCheckbox>
    <RuiMenuSelect
      v-if="state.linked"
      v-model="state.linkedSetting"
      class="pl-7"
      :label="t('accounting_settings.rule.overwrite_by_setting')"
      label-placement="hidden"
      hide-details
      key-attr="identifier"
      text-attr="label"
      :options="linkableSettingOptions"
    >
      <template #selection="{ item }">
        <span class="flex items-center gap-2 text-sm">
          <SuccessDisplay
            :success="item.state"
            size="16"
          />
          {{ item.label }}
        </span>
      </template>
      <template #item="{ item }">
        <span class="flex items-center gap-2 leading-4 font-normal">
          <SuccessDisplay
            :success="item.state"
            size="16"
          />
          {{ item.label }}
        </span>
      </template>
    </RuiMenuSelect>
  </div>
</template>
