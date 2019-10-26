<template>
  <div class="jconfirm jconfirm-light jconfirm-open">
    <div class="jconfirm-bg"></div>
    <div class="jconfirm-scrollpane">
      <div class="jconfirm-row">
        <div class="jconfirm-cell">
          <div
            class="jconfirm-holder"
            style="padding-top: 40px; padding-bottom: 40px;"
          >
            <div class="jc-bs3-container container">
              <div
                class="jc-bs3-row row justify-content-md-center justify-content-sm-center justify-content-xs-center justify-content-lg-center"
              >
                <div
                  class="jconfirm-box-container jconfirm-animated col-md-4 col-md-offset-4 col-sm-6 col-sm-offset-3 col-xs-10 col-xs-offset-1 jconfirm-no-transition"
                >
                  <div
                    class="jconfirm-box jconfirm-hilight-shake jconfirm-type-default jconfirm-type-animated"
                    role="dialog"
                    aria-labelledby="jconfirm-box55253"
                    tabindex="-1"
                  >
                    <div class="jconfirm-closeIcon" style="display: none;">
                      ×
                    </div>
                    <div class="jconfirm-title-c">
                      <span class="jconfirm-icon-c"></span
                      ><span class="jconfirm-title">Sign In</span>
                    </div>
                    <div class="jconfirm-content-pane no-scroll">
                      <div id="jconfirm-box55253" class="jconfirm-content">
                        <div>
                          <div class="form-group input-group">
                            <span class="input-group-addon">User Name:</span
                            ><input
                              id="username_entry"
                              v-model="username"
                              class="form-control"
                              type="text"
                            />
                          </div>
                          <div class="form-group input-group">
                            <span class="input-group-addon">Password:</span
                            ><input
                              id="password_entry"
                              v-model="password"
                              class="form-control"
                              type="password"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                    <div class="jconfirm-buttons">
                      <button
                        type="button"
                        class="btn btn-blue"
                        @click="login()"
                      >
                        Sign In
                      </button>
                      <button type="button" class="btn btn-blue">
                        Create New Account
                      </button>
                    </div>
                    <div class="jconfirm-clear"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { Credentials } from '@/typing/types';
import { verify_userpass } from '@/legacy/userunlock';

@Component({})
export default class Login extends Vue {
  username: string = '';
  password: string = '';

  login() {
    if (!verify_userpass(this.username, this.password)) {
      return;
    }
    const credentials: Credentials = {
      username: this.username,
      password: this.password
    };
    this.$emit('login', credentials);
  }
}
</script>

<style scoped></style>
