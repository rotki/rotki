import { Component, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';

@Component({
  computed: {
    ...mapState('session', ['privacyMode'])
  }
})
export default class PrivacyMixin extends Vue {
  privacyMode!: boolean;
  get privacyStyle(): { [cssClass: string]: string } | null {
    return this.privacyMode
      ? {
          filter: 'blur(0.75em)'
        }
      : null;
  }
}
