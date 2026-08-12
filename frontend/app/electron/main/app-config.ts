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
  };
}
