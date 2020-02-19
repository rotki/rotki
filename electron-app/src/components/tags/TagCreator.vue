<template>
  <v-form ref="form" v-model="valid">
    <v-row>
      <tag-icon class="tag-creator__preview" :tag="tag"></tag-icon>
      <v-tooltip bottom>
        <template #activator="{ on }">
          <v-btn
            icon
            text
            class="tag-creator__random"
            v-on="on"
            @click="randomize"
          >
            <v-icon color="primary">fa-refresh</v-icon>
          </v-btn>
        </template>
        <span>Creates a random color combination</span>
      </v-tooltip>
    </v-row>
    <v-row no-gutters align="center">
      <v-col cols="12">
        <v-row no-gutters>
          <v-col cols="12">
            <v-text-field
              label="Name"
              :rules="rules"
              :value="tag.name"
              :disabled="editMode"
              @input="changed({ name: $event })"
            ></v-text-field>
          </v-col>
        </v-row>
        <v-row no-gutters>
          <v-col cols="12">
            <v-text-field
              :value="tag.description"
              label="Description"
              @input="changed({ description: $event })"
            ></v-text-field>
          </v-col>
        </v-row>
      </v-col>
    </v-row>
    <v-row align="center" justify="center" no-gutters>
      <v-col cols="6">
        <v-row>
          <v-col cols="12">
            <h3 class="text-center">Foreground</h3>
          </v-col>
        </v-row>
        <v-row no-gutters>
          <v-col cols="12" class="tag-creator__color-picker">
            <v-color-picker
              flat
              mode="hexa"
              hide-mode-switch
              :value="`#${tag.foreground_color}`"
              @update:color="
                changed({ foreground_color: $event.hex.replace('#', '') })
              "
            ></v-color-picker>
          </v-col>
        </v-row>
      </v-col>
      <v-col cols="6">
        <v-row>
          <v-col cols="12">
            <h3 class="text-center">Background</h3>
          </v-col>
        </v-row>
        <v-row no-gutters>
          <v-col cols="12" class="tag-creator__color-picker">
            <v-color-picker
              flat
              hide-mode-switch
              mode="hexa"
              :value="`#${tag.background_color}`"
              @update:color="
                changed({ background_color: $event.hex.replace('#', '') })
              "
            ></v-color-picker>
          </v-col>
        </v-row>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-btn
          class="tag-creator__buttons__save"
          width="100"
          depressed
          color="primary"
          :disabled="!valid"
          @click="save"
        >
          Save
        </v-btn>
        <v-btn v-if="editMode" width="100" depressed @click="cancel">
          Cancel
        </v-btn>
      </v-col>
    </v-row>
  </v-form>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { TagEvent } from '@/components/tags/types';
import { Tag } from '@/typing/types';
import TagIcon from '@/components/tags/TagIcon.vue';
import { invertColor, randomColor } from '@/utils/Color';

@Component({
  components: { TagIcon }
})
export default class TagCreator extends Vue {
  @Prop({ required: true })
  tag!: Tag;
  @Prop({ required: true })
  editMode!: boolean;

  valid: boolean = false;

  readonly rules = [(v: string) => !!v || 'Please provide a tag name'];

  @Emit()
  changed(event: TagEvent): Tag {
    return { ...this.tag, ...event };
  }

  randomize() {
    const backgroundColor = randomColor();
    this.changed({
      background_color: backgroundColor,
      foreground_color: invertColor(backgroundColor)
    });
  }

  @Emit()
  save(): Tag {
    const tag = this.tag;
    // @ts-ignore
    this.$refs.form?.reset();
    return tag;
  }

  @Emit()
  cancel() {
    // @ts-ignore
    this.$refs.form?.reset();
  }
}
</script>

<style scoped lang="scss">
.tag-creator {
  &__preview {
    min-width: 120px;
    margin-left: 12px;
    margin-bottom: 10px;
  }
  &__color-picker {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  &__random {
    margin-left: 16px;
  }
  &__buttons {
    &__save {
      margin-right: 8px;
    }
  }
}
</style>
