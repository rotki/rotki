<template>
  <v-dialog :value="value" max-width="500" persistent @input="input">
    <card>
      <template #title>{{ $t('merge_dialog.title') }}</template>
      <template #subtitle>{{ $t('merge_dialog.subtitle') }}</template>
      <template v-if="!done" #hint>{{ $t('merge_dialog.hint') }}</template>
      <template #buttons>
        <v-spacer />
        <v-btn depressed @click="input(false)">
          <span v-if="done">{{ $t('merge_dialog.close') }}</span>
          <span v-else>
            {{ $t('merge_dialog.cancel') }}
          </span>
        </v-btn>
        <v-btn
          v-if="!done"
          depressed
          color="primary"
          :disabled="!valid || pending"
          :loading="pending"
          @click="merge()"
        >
          {{ $t('merge_dialog.merge') }}
        </v-btn>
      </template>

      <div v-if="done">{{ $t('merge_dialog.done') }}</div>

      <v-form v-else v-model="valid">
        <v-text-field
          v-model="source"
          :label="$t('merge_dialog.source.label')"
          :rules="sourceRules"
          outlined
          :disabled="pending"
          persistent-hint
          :hint="$t('merge_dialog.source_hint')"
          :error-messages="errorMessages"
          @focus="clearErrors()"
        />
        <v-row align="center" justify="center" class="my-4">
          <v-col cols="auto">
            <v-icon>mdi-arrow-down</v-icon>
          </v-col>
        </v-row>
        <asset-select
          v-model="target"
          outlined
          :rules="targetRules"
          :label="$t('merge_dialog.target.label')"
          :disabled="pending"
        />
      </v-form>
    </card>
  </v-dialog>
</template>

<script lang="ts">
import { defineComponent, ref, unref } from '@vue/composition-api';
import i18n from '@/i18n';
import { useAssets } from '@/store/assets';

export default defineComponent({
  name: 'MergeDialog',
  props: {
    value: { required: true, type: Boolean }
  },
  emits: ['input'],
  setup(_, { emit }) {
    const done = ref(false);
    const valid = ref(false);
    const errorMessages = ref<string[]>([]);
    const target = ref('');
    const source = ref('');
    const pending = ref(false);

    const { mergeAssets } = useAssets();

    const reset = () => {
      done.value = false;
      target.value = '';
      source.value = '';
      valid.value = false;
      pending.value = false;
      errorMessages.value = [];
    };

    const clearErrors = () => {
      const elements = unref(errorMessages).length;
      for (let i = 0; i < elements; i++) {
        errorMessages.value = [];
      }
    };

    async function merge() {
      pending.value = true;
      const result = await mergeAssets({
        sourceIdentifier: unref(source),
        targetIdentifier: unref(target)
      });

      if (result.success) {
        done.value = true;
      } else {
        errorMessages.value = [
          ...unref(errorMessages),
          result.message ?? i18n.t('merge_dialog.error').toString()
        ];
      }
      pending.value = false;
    }

    const input = (value: boolean) => {
      emit('input', value);
      setTimeout(() => reset(), 100);
    };

    const sourceRules = [
      (v: string) => !!v || i18n.t('merge_dialog.source.non_empty').toString()
    ];
    const targetRules = [
      (v: string) => !!v || i18n.t('merge_dialog.target.non_empty').toString()
    ];

    return {
      done,
      valid,
      errorMessages,
      target,
      source,
      pending,
      sourceRules,
      targetRules,
      merge,
      input,
      clearErrors
    };
  }
});
</script>
