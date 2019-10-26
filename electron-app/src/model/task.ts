export class Task {
  constructor(
    readonly id: number,
    readonly type: string,
    readonly should_expect_callback: boolean
  ) {}
}
