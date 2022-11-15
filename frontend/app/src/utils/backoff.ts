type BackoffCall<T> = () => Promise<T>;

export async function wait(duration: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, duration));
}

export async function backoff<T>(
  retries: number,
  call: BackoffCall<T>,
  delay = 5000
): Promise<T> {
  let result: T;
  try {
    result = await call();
  } catch (e) {
    if (retries > 1) {
      await wait(delay);
      result = await backoff(retries - 1, call, delay * 2);
    } else {
      throw e;
    }
  }
  return result;
}
