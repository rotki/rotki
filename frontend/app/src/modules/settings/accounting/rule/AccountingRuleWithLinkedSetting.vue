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

const elemID = computed(() => `${identifier}-switch`);
</script>

<template>
  <div class="flex gap-4 py-4">
    <RuiSwitch
      :id="elemID"
      v-model="state.value"
      color="primary"
      :disabled="state.linked"
    />
    <div class="w-full">
      <label
        :for="elemID"
        class="cursor-pointer"
      >
        <div class="text-body-1 text-rui-text">
          {{ label }}
        </div>
        <div class="text-rui-text-secondary text-body-2">
          {{ hint }}
          <ExternalLink
            v-if="learnMoreUrl"
            :url="learnMoreUrl"
            color="primary"
            class="inline-flex items-center gap-1 text-body-2"
            @click.stop
          >
            <RuiIcon
              name="lu-book-open"
              size="14"
            />
            {{ t('accounting_settings.rule.learn_more') }}
          </ExternalLink>
        </div>
      </label>
      <RuiCheckbox
        v-model="linked"
        size="sm"
        color="primary"
        hide-details
      >
        <span class="text-caption">
          {{ t('accounting_settings.rule.overwrite_by_setting') }}
        </span>
      </RuiCheckbox>
      <div
        v-if="state.linked"
        class="ml-7 mt-1 md:w-1/2"
      >
        <RuiMenuSelect
          v-model="state.linkedSetting"
          variant="outlined"
          hide-details
          dense
          key-attr="identifier"
          text-attr="label"
          :options="linkableSettingOptions"
        />
        <div
          v-if="linkedPropertyValue !== null"
          class="flex items-center mt-2 gap-2"
        >
          {{ t('accounting_settings.rule.current_setting_value') }}
          <SuccessDisplay :success="linkedPropertyValue" />
        </div>
      </div>
    </div>
  </div>
</template>
