<script setup lang="ts">
import type { XpubPayload } from '@/modules/accounts/blockchain-accounts';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { BtcChains } from '@/modules/core/common/chains';
import { Blockchain } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { isEmpty } from 'es-toolkit/compat';
import { type DetectionResult, detectXpubType, getKeyType, getPrefix, XpubPrefix } from '@/modules/accounts/xpub';
import { trimOnPaste } from '@/modules/core/common/helpers/event';
import { toMessages } from '@/modules/core/common/validation/validation';

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

const xpubKey = ref<string>('');
const derivationPath = ref<string>('');
const xpubKeyPrefix = ref<XpubPrefix>(XpubPrefix.ZPUB);
const advanced = ref<boolean>(false);
const detectedType = ref<DetectionResult>();
const showDisambiguation = ref<boolean>(false);

const v$ = useVuelidate(
  {
    derivationPath: {
      basic: () => true,
    },
    xpub: {
      required: helpers.withMessage(t('account_form.validation.xpub_non_empty'), required),
    },
  },
  {
    derivationPath,
    xpub,
  },
  {
    $autoDirty: true,
    $externalResults: errors,
    $stopPropagation: true,
  },
);

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

function defaultPrefixFor(chain: BtcChains): XpubPrefix {
  return chain === Blockchain.BCH ? XpubPrefix.XPUB : XpubPrefix.ZPUB;
}

function normalizeDerivationPath(path: string): string {
  return path.replace(/'/g, '').replace(/\/$/, '');
}

function runDetection(value: string): void {
  const result = detectXpubType(value);
  set(detectedType, result);
  set(showDisambiguation, false);

  if (result === 'address') {
    emit('detected-address', value.trim());
    return;
  }

  if (result === XpubPrefix.YPUB || result === XpubPrefix.ZPUB) {
    set(xpubKeyPrefix, result);
    return;
  }

  if (result === 'ambiguous') {
    set(xpubKeyPrefix, defaultPrefixFor(blockchain));
    if (blockchain !== Blockchain.BCH)
      set(showDisambiguation, true);
  }
}

function resolveDisambiguation(choice: XpubPrefix): void {
  set(xpubKeyPrefix, choice);
  set(detectedType, choice);
}

function onPasteXpub(event: ClipboardEvent): void {
  if (disabled)
    return;

  const paste = trimOnPaste(event);
  if (paste)
    set(xpubKey, paste);
}

function samePayload(a: XpubPayload | undefined, b: XpubPayload | undefined): boolean {
  return a?.xpub === b?.xpub
    && a?.xpubType === b?.xpubType
    && a?.derivationPath === b?.derivationPath;
}

function validate(): Promise<boolean> {
  return get(v$).$validate();
}

watch(errors, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

watchImmediate(xpub, (xpubVal: XpubPayload | undefined) => {
  const nextXpub = xpubVal?.xpub ?? '';
  const nextPath = xpubVal?.derivationPath ?? '';
  set(xpubKey, nextXpub);

  if (normalizeDerivationPath(get(derivationPath)) !== nextPath)
    set(derivationPath, nextPath);

  if (!xpubVal?.xpubType)
    return;

  const prefix = getPrefix(xpubVal.xpubType);
  set(xpubKeyPrefix, prefix);
  if (disabled && nextXpub)
    set(detectedType, prefix);
});

watch(() => blockchain, (chain) => {
  set(xpubKeyPrefix, defaultPrefixFor(chain));
});

watch(xpubKey, (newKey) => {
  if (!newKey) {
    set(detectedType, undefined);
    set(showDisambiguation, false);
    return;
  }
  runDetection(newKey);
});

watch([xpubKeyPrefix, xpubKey, derivationPath], ([prefix, key, path]) => {
  const next: XpubPayload | undefined = key
    ? {
        derivationPath: normalizeDerivationPath(path),
        xpub: key.trim(),
        xpubType: getKeyType(prefix),
      }
    : undefined;

  if (!samePayload(get(xpub), next))
    set(xpub, next);
});

defineExpose({
  validate,
});
</script>

<template>
  <div class="mt-2 flex flex-col gap-4">
    <div class="flex gap-4">
      <RuiTextField
        v-model="xpubKey"
        variant="outlined"
        color="primary"
        class="account-form__xpub flex-1"
        :label="t('account_form.labels.btc.xpub')"
        autocomplete="off"
        :hint="detectedHint"
        :error-messages="toMessages(v$.xpub)"
        :disabled="disabled"
        @blur="v$.xpub.$touch()"
        @paste="onPasteXpub($event)"
      />
      <div>
        <RuiTooltip
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <div class="account-form__advanced">
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
      data-cy="xpub-disambiguation"
    >
      <span class="text-rui-text-secondary text-body-2">
        {{ t('account_form.xpub_detected.disambiguation_prompt') }}
      </span>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
        <RuiButton
          v-for="option in disambiguationOptions"
          :key="option.value"
          :variant="xpubKeyPrefix === option.value ? 'default' : 'outlined'"
          color="primary"
          size="sm"
          :disabled="disabled"
          :data-cy="`xpub-disambiguation-${option.value}`"
          @click="resolveDisambiguation(option.value)"
        >
          <div class="flex flex-col items-start">
            <span>{{ option.label }}</span>
            <span
              class="text-caption"
              :class="xpubKeyPrefix === option.value ? 'opacity-70' : 'text-rui-text-secondary'"
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
        v-model="derivationPath"
        variant="outlined"
        color="primary"
        class="account-form__derivation-path"
        :label="t('account_form.labels.btc.derivation_path')"
        :error-messages="toMessages(v$.derivationPath)"
        autocomplete="off"
        :disabled="disabled"
        :hint="t('common.optional')"
        @blur="v$.derivationPath.$touch()"
      />
    </div>
  </div>
</template>
