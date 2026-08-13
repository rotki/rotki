export interface AppConfig {
  readonly isDev: boolean;
  readonly isMac: boolean;
  /**
   * The origin the renderer addresses. Set once starling's proxy port is known:
   * core answers `/api/1/*` and `/ws/` under it, colibri `/colibri/*`.
   */
  apiUrl: string;
  readonly ports: {
    colibriPort: number;
    corePort: number;
    mcpPort: number;
    proxyPort: number;
    /**
     * Dev only: the premium dev-proxy's port, when `pnpm dev` started one.
     * starling forwards `/api/1/*` there instead of straight to core, so the
     * proxy can serve locally built premium components. Undefined in every
     * packaged build and in any dev run without the proxy.
     */
    coreUpstreamPort?: number;
  };
}
