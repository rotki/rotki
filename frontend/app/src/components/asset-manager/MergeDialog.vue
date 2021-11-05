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
          @focus="removeErrors()"
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
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import { AssetMergePayload } from '@/store/assets/types';
import { ActionStatus } from '@/store/types';

@Component({
  name: 'MergeDialog',
  methods: {
    ...mapActions('assets', ['mergeAssets'])
  }
})
export default class MergeDialog extends Vue {
  @Prop({ required: true, type: Boolean })
  value!: boolean;
  @Emit()
  input(_value: boolean) {
    setTimeout(() => this.reset(), 100);
  }

  private reset() {
    this.done = false;
    this.target = '';
    this.source = '';
    this.valid = false;
    this.pending = false;
    this.errorMessages = [];
  }

  mergeAssets!: (payload: AssetMergePayload) => Promise<ActionStatus>;

  done: boolean = false;
  valid: boolean = false;
  errorMessages: string[] = [];

  target: string = '';
  source: string = '';

  pending: boolean = false;

  readonly sourceRules = [
    (v: string) => !!v || this.$t('merge_dialog.source.non_empty').toString()
  ];
  readonly targetRules = [
    (v: string) => !!v || this.$t('merge_dialog.target.non_empty').toString()
  ];

  removeErrors() {
    const elements = this.errorMessages.length;
    for (let i = 0; i < elements; i++) {
      this.errorMessages.pop();
    }
  }

  async merge() {
    this.pending = true;
    const { success, message } = await this.mergeAssets({
      sourceIdentifier: this.source,
      targetIdentifier: this.target
    });

    if (success) {
      this.done = true;
    } else {
      this.errorMessages.push(
        message ?? this.$t('merge_dialog.error').toString()
      );
    }
    this.pending = false;
  }
}
</script>
