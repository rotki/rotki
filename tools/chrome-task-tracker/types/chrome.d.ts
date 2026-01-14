/**
 * Minimal Chrome DevTools Extension API type definitions
 * For full types, install @types/chrome
 */

declare namespace chrome {
  namespace devtools {
    namespace panels {
      /** Current DevTools theme: 'default', 'dark', or 'light' */
      const themeName: string;

      /**
       * Creates a new DevTools panel
       * @param title Panel title shown in DevTools
       * @param iconPath Path to panel icon (can be empty string)
       * @param pagePath Path to the panel's HTML page
       * @param callback Called when panel is created
       */
      function create(
        title: string,
        iconPath: string,
        pagePath: string,
        callback?: (panel: ExtensionPanel) => void
      ): void;

      interface ExtensionPanel {
        onShown: Event<(window: Window) => void>;
        onHidden: Event<() => void>;
      }

      interface Event<T extends (...args: any[]) => void> {
        addListener(callback: T): void;
        removeListener(callback: T): void;
      }
    }

    namespace network {
      /**
       * Fired when a network request finishes
       */
      const onRequestFinished: NetworkEvent;

      interface NetworkEvent {
        addListener(callback: (request: HAREntry) => void): void;
        removeListener(callback: (request: HAREntry) => void): void;
      }
    }

    namespace inspectedWindow {
      /** The ID of the tab being inspected */
      const tabId: number;

      /**
       * Evaluates a JavaScript expression in the inspected page
       */
      function eval(
        expression: string,
        callback?: (result: any, exceptionInfo: ExceptionInfo) => void
      ): void;

      interface ExceptionInfo {
        isError: boolean;
        isException: boolean;
        value: string;
      }
    }
  }

  namespace runtime {
    const onInstalled: RuntimeEvent;
    const onMessage: MessageEvent;

    interface RuntimeEvent {
      addListener(callback: () => void): void;
    }

    interface MessageEvent {
      addListener(
        callback: (
          message: any,
          sender: MessageSender,
          sendResponse: (response?: any) => void
        ) => boolean | void
      ): void;
    }

    interface MessageSender {
      tab?: { id: number };
      frameId?: number;
      id?: string;
      url?: string;
    }
  }
}

/**
 * HAR Entry - represents a single network request
 * @see http://www.softwareishard.com/blog/har-12-spec/
 */
interface HAREntry {
  /** Start time of the request */
  startedDateTime: string;

  /** Total elapsed time in milliseconds */
  time: number;

  /** Request details */
  request: HARRequest;

  /** Response details */
  response: HARResponse;

  /**
   * Gets the response body content
   * @param callback Called with content and encoding
   */
  getContent(callback: (content: string, encoding: string) => void): void;
}

interface HARRequest {
  /** HTTP method (GET, POST, etc.) */
  method: string;

  /** Absolute URL of the request */
  url: string;

  /** HTTP version */
  httpVersion: string;

  /** Request headers */
  headers: HARHeader[];

  /** Query string parameters */
  queryString: HARQueryString[];

  /** Posted data (for POST/PUT requests) */
  postData?: HARPostData;

  /** Total size of headers */
  headersSize: number;

  /** Total size of body */
  bodySize: number;
}

interface HARResponse {
  /** HTTP status code */
  status: number;

  /** HTTP status text */
  statusText: string;

  /** HTTP version */
  httpVersion: string;

  /** Response headers */
  headers: HARHeader[];

  /** Response content */
  content: HARContent;

  /** Redirect URL if any */
  redirectURL: string;

  /** Total size of headers */
  headersSize: number;

  /** Total size of body */
  bodySize: number;
}

interface HARHeader {
  name: string;
  value: string;
}

interface HARQueryString {
  name: string;
  value: string;
}

interface HARPostData {
  /** MIME type */
  mimeType: string;

  /** Posted text content */
  text?: string;

  /** Posted form parameters */
  params?: HARParam[];
}

interface HARParam {
  name: string;
  value?: string;
  fileName?: string;
  contentType?: string;
}

interface HARContent {
  /** Content size in bytes */
  size: number;

  /** Content compression (bytes saved) */
  compression?: number;

  /** MIME type */
  mimeType: string;

  /** Response text (may be encoded) */
  text?: string;

  /** Encoding (e.g., 'base64') */
  encoding?: string;
}