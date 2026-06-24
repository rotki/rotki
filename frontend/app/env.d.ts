// env.d.ts
/// <reference types="vite/client" />
/// <reference types="@intlify/unplugin-vue-i18n/messages" />
/// <reference types="vue-i18n" />
/// <reference types="@rotki/ui-library/vite-plugin/client" />

interface ImportMetaEnv {
  readonly VITE_WALLET_CONNECT_PROJECT_ID: string;
}
