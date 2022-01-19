<template>
  <v-card flat>
    <v-card-title>
      {{ title }}
    </v-card-title>
    <v-card-subtitle>
      {{ description }}
    </v-card-subtitle>
    <v-card-text class="service-key__content">
      <v-row justify="center">
        <v-col>
          <revealable-input
            outlined
            :value="editMode ? currentValue : ''"
            class="service-key__api-key"
            :hint="currentValue ? '' : hint"
            :disabled="!editMode"
            :label="label"
            @input="currentValue = $event"
            @paste="onPaste"
          />
        </v-col>
        <v-col cols="auto">
          <v-tooltip top>
            <template #activator="{ on }">
              <v-btn
                icon
                text
                class="service-key__content__delete"
                :disabled="loading || !currentValue"
                color="primary"
                v-on="on"
                @click="deleteKey()"
              >
                <v-icon>mdi-delete</v-icon>
              </v-btn>
            </template>
            <span>
              {{ tooltip }}
            </span>
          </v-tooltip>
        </v-col>
      </v-row>
      <v-row v-if="$slots.default">
        <v-col>
          <slot />
        </v-col>
      </v-row>
    </v-card-text>
    <v-card-actions class="service-key__buttons">
      <v-btn
        class="service-key__buttons__save"
        depressed
        color="primary"
        :disabled="(editMode && currentValue === '') || loading"
        @click="save()"
        v-text="
          editMode
            ? $t('service_key.actions.save')
            : $t('service_key.actions.edit')
        "
      />
      <v-btn
        v-if="editMode && cancellable"
        class="service-key__buttons__cancel"
        depressed
        color="primary"
        @click="cancel()"
        v-text="$t('service_key.actions.cancel')"
      />
    </v-card-actions>
  </v-card>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { trimOnPaste } from '@/utils/event';

@Component({
  components: {
    RevealableInput
  }
})
export default class ServiceKey extends Vue {
  @Prop({ required: true })
  value!: string;
  @Prop({ required: true })
  title!: string;
  @Prop({ required: false, default: '' })
  description!: string;
  @Prop({ required: false, default: false })
  loading!: boolean;
  @Prop({ required: false, default: '' })
  tooltip!: string;
  @Prop({ required: false, default: '' })
  hint!: string;
  @Prop({ required: false, default: '' })
  label!: string;

  currentValue: string = '';

  editMode: boolean = false;
  cancellable: boolean = false;

  onPaste(event: ClipboardEvent) {
    const paste = trimOnPaste(event);
    if (paste) {
      this.currentValue = paste;
    }
  }

  mounted() {
    this.updateStatus();
  }

  @Watch('value')
  onValueChange() {
    this.updateStatus();
  }

  private updateStatus() {
    if (this.value === '') {
      this.cancellable = false;
      this.editMode = true;
    } else {
      this.cancellable = true;
      this.editMode = false;
    }
    this.currentValue = this.value;
  }

  @Emit()
  deleteKey() {}

  save() {
    if (this.editMode) {
      this.$emit('save', this.currentValue);
      this.editMode = false;
      this.cancellable = true;
    } else {
      this.editMode = true;
    }
  }

  cancel() {
    this.editMode = false;
    this.currentValue = this.value;
  }

  @Emit()
  input(_value: string) {}
}
</script>

<style scoped lang="scss">
.service-key {
  &__buttons {
    padding: 16px !important;
  }

  &__content {
    &__delete {
      margin-top: 10px;
    }

    ::v-deep {
      .v-input {
        &--is-disabled {
          .v-icon,
          .v-label {
            color: green !important;
          }
        }
      }
    }
  }
}
</style>
