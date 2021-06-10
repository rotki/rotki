<template>
  <v-form ref="form" v-model="valid">
    <v-row>
      <tag-icon class="tag-creator__preview" :tag="tag" />
      <v-tooltip bottom>
        <template #activator="{ on }">
          <v-btn
            icon
            text
            class="tag-creator__random"
            v-on="on"
            @click="randomize"
          >
            <v-icon color="primary">mdi-refresh</v-icon>
          </v-btn>
        </template>
        <span>
          {{ $t('tag_creator.refresh_tooltip') }}
        </span>
      </v-tooltip>
    </v-row>
    <v-row no-gutters align="center" class="mt-4">
      <v-col cols="12">
        <v-row no-gutters>
          <v-col cols="12">
            <v-text-field
              outlined
              class="tag_creator__name"
              :label="$t('tag_creator.labels.name')"
              :rules="rules"
              :value="tag.name"
              :disabled="editMode"
              @input="changed({ name: $event })"
            />
          </v-col>
        </v-row>
        <v-row no-gutters>
          <v-col cols="12">
            <v-text-field
              outlined
              class="tag_creator__description"
              :value="tag.description"
              :label="$t('tag_creator.labels.description')"
              @input="changed({ description: $event })"
            />
          </v-col>
        </v-row>
      </v-col>
    </v-row>
    <v-row align="center" justify="center" no-gutters>
      <v-col cols="6">
        <v-row>
          <v-col cols="12">
            <div class="text-h6 text-center">
              {{ $t('tag_creator.labels.foreground') }}
            </div>
          </v-col>
        </v-row>
        <v-row no-gutters>
          <v-col cols="12" class="tag-creator__color-picker">
            <v-color-picker
              flat
              class="tag-creator__color-picker__foreground"
              mode="hexa"
              hide-mode-switch
              :value="`#${tag.foreground_color}`"
              @update:color="
                changed({ foreground_color: $event.hex.replace('#', '') })
              "
            />
          </v-col>
        </v-row>
      </v-col>
      <v-col cols="6">
        <v-row>
          <v-col cols="12">
            <div class="text-h6 text-center">
              {{ $t('tag_creator.labels.background') }}
            </div>
          </v-col>
        </v-row>
        <v-row no-gutters>
          <v-col cols="12" class="tag-creator__color-picker">
            <v-color-picker
              class="tag-creator__color-picker__background"
              flat
              hide-mode-switch
              mode="hexa"
              :value="`#${tag.background_color}`"
              @update:color="
                changed({ background_color: $event.hex.replace('#', '') })
              "
            />
          </v-col>
        </v-row>
      </v-col>
    </v-row>
    <v-row class="mb-2">
      <v-col cols="12">
        <v-btn
          class="tag-creator__buttons__save"
          width="100"
          depressed
          color="primary"
          :disabled="!valid"
          @click="save"
        >
          {{ $t('tag_creator.buttons.save') }}
        </v-btn>
        <v-btn v-if="editMode" width="100" depressed @click="cancel">
          {{ $t('tag_creator.buttons.cancel') }}
        </v-btn>
      </v-col>
    </v-row>
  </v-form>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import TagIcon from '@/components/tags/TagIcon.vue';
import { TagEvent } from '@/components/tags/types';
import { Tag } from '@/typing/types';
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

  readonly rules = [
    (v: string) =>
      !!v || this.$t('tag_creator.validation.empty_name').toString()
  ];

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
