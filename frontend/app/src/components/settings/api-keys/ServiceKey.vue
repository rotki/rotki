<template>
  <v-card>
    <v-card-title>
      {{ title }}
    </v-card-title>
    <v-card-text class="service-key__content" style="display: block;">
      <div>
        {{ description }}
      </div>
      <div style="display: flex; align-items: center;">
        <revealable-input
          :value="editMode ? currentValue : ''"
          class="service-key__api-key"
          :hint="currentValue ? '' : hint"
          :disabled="!editMode"
          :label="label"
          @input="currentValue = $event"
        ></revealable-input>
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
              <v-icon>fa-trash</v-icon>
            </v-btn>
          </template>
          <span>
            {{ tooltip }}
          </span>
        </v-tooltip>
      </div>
    </v-card-text>
    <v-card-actions>
      <v-btn
        class="service-key__buttons__save"
        depressed
        color="primary"
        :disabled="(editMode && currentValue === '') || loading"
        @click="save()"
      >
        {{ editMode ? 'Save' : 'Edit' }}
      </v-btn>
      <v-btn
        v-if="editMode && cancellable"
        class="service-key__buttons__cancel"
        depressed
        color="primary"
        @click="cancel()"
      >
        Cancel
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import RevealableInput from '@/components/inputs/RevealableInput.vue';

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
.service-key__content {
  flex-direction: row;
  display: flex;
  align-items: center;

  &__delete {
    max-width: 24px;
    margin-left: 16px;
  }

  ::v-deep .v-input--is-disabled {
    .v-icon,
    .v-label {
      color: green !important;
    }
  }
}
</style>
