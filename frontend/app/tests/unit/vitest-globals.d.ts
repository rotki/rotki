import 'vitest';

declare module 'vitest' {
  interface VitestUtils {
    delay: (ms?: number) => Promise<void>;
  }
}
