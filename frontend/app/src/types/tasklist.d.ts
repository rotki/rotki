declare module 'tasklist' {
  function tasklist(): Promise<tasklist.Task[]>;
  export = tasklist;
}

declare namespace tasklist {
  interface Task {
    imageName: string;
    pid: number;
    sessionName: string;
    sessionNumber: number;
    memUsage: number;
  }
}
