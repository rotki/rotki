<script setup lang="ts">
import type { XpubPayload } from '@/modules/accounts/blockchain-accounts';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { BtcChains } from '@/modules/core/common/chains';
import { z, type ZodType } from 'zod';
import { useXpubInput, type XpubFormState } from '@/modules/accounts/blockchain/use-xpub-input';
import { XpubPrefix } from '@/modules/accounts/xpub';
import { trimOnPaste } from '@/modules/core/common/helpers/event';
import { requiredField } from '@/modules/core/form/fields';
import { toServerErrors } from '@/modules/core/form/server-errors';
import { useForm } from '@/modules/core/form/use-form';

interface DisambiguationOption {
  readonly value: XpubPrefix;
  readonly label: string;
  readonly description: string;
}

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });

const xpub = defineModel<XpubPayload | undefined>('xpub');

const { disabled, blockchain } = defineProps<{
  disabled: boolean;
  blockchain: BtcChains;
}>();

const emit = defineEmits<{
  'detected-address': [address: string];
}>();

const { t } = useI18n({ useScope: 'global' });

const advanced = ref<boolean>(false);

/**
 * Only the key is validated. The derivation path had a rule that always passed, whose one purpose
 * was to give the backend's errors for that field somewhere to render; the core keys those by
 * field rather than by rule, so it needs nothing here.
 */
const schema = computed<ZodType>(() => z.object({
  xpub: requiredField(t('account_form.validation.xpub_non_empty')),
}));

const { errors: fieldErrors, setServerErrors, state, touch, validate } = useForm<XpubFormState, XpubFormState>({
  initial: (): XpubFormState => ({ derivationPath: '', xpub: '' }),
  schema,
  // The assembled payload is handed to the parent as it is typed; there is nothing to submit here.
  submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
  transform: (state): XpubFormState => ({ ...state }),
});

const { detectedType, prefix, resolveDisambiguation, showDisambiguation } = useXpubInput(state, xpub, {
  blockchain: () => blockchain,
  disabled: () => disabled,
  onAddressDetected: (address: string): void => {
    emit('detected-address', address);
  },
});

watchImmediate(errors, (value) => {
  setServerErrors(toServerErrors(value));
}, { deep: true });

const detectedHint = computed<string | undefined>(() => {
  const detected = get(detectedType);
  if (detected === XpubPrefix.YPUB)
    return t('account_form.xpub_detected.type_hint', { type: t('account_form.xpub_detected.segwit') });
  if (detected === XpubPrefix.ZPUB)
    return t('account_form.xpub_detected.type_hint', { type: t('account_form.xpub_detected.native_segwit') });
  return undefined;
});

const disambiguationOptions = computed<DisambiguationOption[]>(() => [
  {
    description: t('account_form.xpub_detected.native_segwit_description'),
    label: t('account_form.xpub_detected.native_segwit'),
    value: XpubPrefix.ZPUB,
  },
  {
    description: t('account_form.xpub_detected.segwit_description'),
    label: t('account_form.xpub_detected.segwit'),
    value: XpubPrefix.YPUB,
  },
  {
    description: t('account_form.xpub_detected.taproot_description'),
    label: t('account_form.xpub_detected.taproot'),
    value: XpubPrefix.P2TR,
  },
  {
    description: t('account_form.xpub_detected.legacy_description'),
    label: t('account_form.xpub_detected.legacy'),
    value: XpubPrefix.XPUB,
  },
]);

function onPasteXpub(event: ClipboardEvent): void {
  if (disabled)
    return;

  const paste = trimOnPaste(event);
  if (paste)
    state.xpub = paste;
}

defineExpose({
  validate,
});
</script>

<template>
  <div class="mt-2 flex flex-col gap-4">
    <div class="flex gap-4">
      <RuiTextField
        v-model="state.xpub"
        variant="outlined"
        color="primary"
        class="flex-1"
        data-testid="xpub-key"
        :label="t('account_form.labels.btc.xpub')"
        autocomplete="off"
        :hint="detectedHint"
        :error-messages="fieldErrors('xpub')"
        :disabled="disabled"
        @update:model-value="touch('xpub')"
        @paste="onPasteXpub($event)"
      />
      <div>
        <RuiTooltip
          :options="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <div data-testid="xpub-advanced-toggle">
              <RuiButton
                variant="text"
                icon
                class="mt-1"
                @click="advanced = !advanced"
              >
                <RuiIcon :name="advanced ? 'lu-chevron-up' : 'lu-chevron-down'" />
              </RuiButton>
            </div>
          </template>
          <span>
            {{ t('account_form.advanced_tooltip', advanced ? 0 : 1) }}
          </span>
        </RuiTooltip>
      </div>
    </div>

    <div
      v-if="showDisambiguation"
      class="flex flex-col gap-2 -mt-2 mb-3"
      data-testid="xpub-disambiguation"
    >
      <span class="text-rui-text-secondary text-body-2">
        {{ t('account_form.xpub_detected.disambiguation_prompt') }}
      </span>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
        <RuiButton
          v-for="option in disambiguationOptions"
          :key="option.value"
          :variant="prefix === option.value ? 'default' : 'outlined'"
          color="primary"
          size="sm"
          :disabled="disabled"
          data-testid="xpub-disambiguation-option"
          :data-key="option.value"
          @click="resolveDisambiguation(option.value)"
        >
          <div class="flex flex-col items-start">
            <span>{{ option.label }}</span>
            <span
              class="text-caption"
              :class="prefix === option.value ? 'opacity-70' : 'text-rui-text-secondary'"
            >
              {{ option.description }}
            </span>
          </div>
        </RuiButton>
      </div>
      <span
        v-if="!disabled"
        class="text-rui-text-secondary text-caption"
      >
        {{ t('account_form.xpub_detected.disambiguation_hint') }}
      </span>
    </div>

    <div v-if="advanced">
      <RuiTextField
        v-model="state.derivationPath"
        variant="outlined"
        color="primary"
        data-testid="xpub-derivation-path"
        :label="t('account_form.labels.btc.derivation_path')"
        :error-messages="fieldErrors('derivationPath')"
        autocomplete="off"
        :disabled="disabled"
        :hint="t('common.optional')"
      />
    </div>
  </div>
</template>
