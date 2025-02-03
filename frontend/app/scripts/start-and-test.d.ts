declare module 'start-server-and-test' {
  interface Service {
    start: string;
    url: string;
  }

  interface Options {
    test: string;
    services: Service[];
    namedArguments?: Record<string, any>;
  }

  export function startAndTest(options: Options): Promise<void>;
}
