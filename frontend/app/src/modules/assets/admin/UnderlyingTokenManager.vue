<script setup lang="ts">
import { EvmTokenKind, isValidEthAddress, type UnderlyingToken } from '@rotki/common';
import { z, type ZodType } from 'zod';
import UnderlyingTokenWeightHint from '@/modules/assets/admin/UnderlyingTokenWeightHint.vue';
import { evmTokenKindsData } from '@/modules/core/common/chains';
import { useForm } from '@/modules/core/form/use-form';
import RowActions from '@/modules/shell/components/RowActions.vue';
import SimpleTable from '@/modules/shell/components/SimpleTable.vue';

const modelValue = defineModel<UnderlyingToken[]>({ required: true });

const { t } = useI18n({ useScope: 'global' });

/** Vuelidate's `req`, which reports presence without trimming, so `'  '` counts as present. */
function isPresent(value: string): boolean {
  return value.length > 0;
}

/**
 * The staging row, not the list it feeds. Both fields report every rule they break, in the order
 * vuelidate evaluated them, so an emptied address is still both malformed and missing.
 *
 * The range rule rejects any value carrying whitespace, which is what `between` did before
 * comparing, so `' 50'` is out of range rather than merely oddly typed.
 */
const schema = computed<ZodType>(() => z.object({
  address: z.string().superRefine((value, ctx) => {
    if (!isValidEthAddress(value))
      ctx.addIssue({ code: 'custom', message: t('underlying_token_manager.validation.valid') });

    if (value.trim() === '')
      ctx.addIssue({ code: 'custom', message: t('underlying_token_manager.validation.address_non_empty') });
  }),
  tokenKind: z.enum(EvmTokenKind),
  weight: z.string().superRefine((value, ctx) => {
    const weight = Number(value);
    if (isPresent(value) && (/\s/.test(value) || !(weight >= 1 && weight <= 100)))
      ctx.addIssue({ code: 'custom', message: t('underlying_token_manager.validation.out_of_range') });

    if (isPresent(value) && !/^\d*(?:\.\d+)?$/.test(value))
      ctx.addIssue({ code: 'custom', message: t('underlying_token_manager.validation.not_valid') });

    if (value.trim() === '')
      ctx.addIssue({ code: 'custom', message: t('underlying_token_manager.validation.non_empty') });
  }),
}));

/**
 * The row is invalid whenever it is empty, which is most of the time, and it must never block the
 * asset form that owns the list. Vuelidate needed $stopPropagation for that; a zod form joins no
 * parent tree, so the isolation comes for free.
 */
const form = useForm<UnderlyingToken, UnderlyingToken>({
  initial: (): UnderlyingToken => ({ address: '', tokenKind: EvmTokenKind.ERC20, weight: '' }),
  schema,
  submit: async (token: UnderlyingToken): Promise<{ success: boolean }> => {
    const underlyingTokens = [...get(modelValue)];
    const index = underlyingTokens.findIndex(({ address }) => address === token.address);

    if (index >= 0)
      underlyingTokens[index] = token;
    else underlyingTokens.push(token);

    set(modelValue, underlyingTokens);
    return Promise.resolve({ success: true });
  },
  transform: (state): UnderlyingToken => ({
    address: state.address,
    tokenKind: state.tokenKind,
    weight: state.weight,
  }),
});

// Destructured, because a ref reached through `form.` in the template is not unwrapped and would
// read as permanently truthy.
const { valid } = form;

function deleteToken(address: string): void {
  set(
    modelValue,
    [...get(modelValue)].filter(({ address: tokenAddress }) => tokenAddress !== address),
  );
}

async function addToken(): Promise<void> {
  const result = await form.submit();
  if (result.outcome === 'success')
    form.reset();
}

function editToken(token: UnderlyingToken): void {
  form.state.address = token.address;
  form.state.tokenKind = token.tokenKind;
  form.state.weight = token.weight;
  deleteToken(token.address);
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="text-h6">
      {{ t('underlying_token_manager.labels.tokens') }}
    </div>

    <form
      novalidate
      class="grid md:grid-cols-2 lg:grid-cols-4 gap-x-4 gap-y-2 my-2"
      @submit.stop.prevent="addToken()"
    >
      <div class="md:col-span-2">
        <RuiTextField
          v-model="form.state.address"
          :error-messages="form.errors('address')"
          data-testid="underlying-token-address"
          variant="outlined"
          color="primary"
          :label="t('common.address')"
          @update:model-value="form.touch('address')"
        />
      </div>

      <div class="col-span-1">
        <RuiMenuSelect
          v-model="form.state.tokenKind"
          :label="t('asset_form.labels.token_kind')"
          :options="evmTokenKindsData"
          key-attr="identifier"
          text-attr="label"
          variant="outlined"
        />
      </div>

      <div class="col-span-1">
        <RuiTextField
          v-model="form.state.weight"
          variant="outlined"
          color="primary"
          type="number"
          max="100"
          min="1"
          :error-messages="form.errors('weight')"
          data-testid="underlying-token-weight"
          :label="t('underlying_token_manager.labels.weight')"
          @update:model-value="form.touch('weight')"
        >
          <template #append>
            <UnderlyingTokenWeightHint />
          </template>
        </RuiTextField>
      </div>

      <RuiButton
        color="primary"
        class="col-span-2 lg:col-span-4"
        :disabled="!valid"
        type="submit"
        data-testid="underlying-token-add"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('common.actions.add') }}
      </RuiButton>
    </form>

    <SimpleTable class="underlying-tokens min-h-24">
      <thead>
        <tr>
          <th scope="col">
            {{ t('common.address') }}
          </th>
          <th scope="col">
            {{ t('underlying_token_manager.tokens.token_kind') }}
          </th>
          <th scope="col">
            {{ t('underlying_token_manager.tokens.weight') }}
          </th>
          <th scope="col" />
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="token in modelValue"
          :key="token.address"
        >
          <td class="grow">
            {{ token.address }}
          </td>
          <td class="shrink">
            {{ token.tokenKind.toUpperCase() }}
          </td>
          <td class="shrink text-no-wrap">
            {{
              t('underlying_token_manager.tokens.weight_percentage', {
                weight: token.weight,
              })
            }}
          </td>
          <td>
            <RowActions
              :edit-tooltip="t('underlying_token_manager.edit_tooltip')"
              :delete-tooltip="t('underlying_token_manager.delete_tooltip')"
              @delete-click="deleteToken(token.address)"
              @edit-click="editToken(token)"
            />
          </td>
        </tr>
      </tbody>
    </SimpleTable>
  </div>
</template>
