import type { ComputedRef, UnwrapNestedRefs } from 'vue';
import type { ZodType } from 'zod';
import { isEqual } from 'es-toolkit';

function isRecord(value: unknown): value is object {
  return value !== null && typeof value === 'object';
}

/**
 * Result of a submit attempt. A plain discriminated union rather than a `Result` type, so the core
 * carries no dependency of its own; the API edge can wrap it if it wants to.
 */
export type FormOutcome<TPayload, TMessage = string> =
  | { readonly outcome: 'success'; readonly payload: TPayload }
  | { readonly outcome: 'invalid' }
  | { readonly message?: TMessage; readonly outcome: 'error' };

export interface FormOptions<TState extends object, TPayload, TMessage = string> {
  /** Create-default or edit seed. Called on construction and by `reset()`. */
  readonly initial: () => TState;
  /** The single validation source of truth. Messages carry i18n keys, resolved here via `t()`. */
  readonly schema: ZodType;
  /** UI state -> API payload (trim, empty->null, BigNumber, ...). Pure. */
  readonly transform: (state: UnwrapNestedRefs<TState>) => TPayload;
  /** Injected persistence, returning the store/API `ActionStatus`. */
  readonly submit: (payload: TPayload) => Promise<{ readonly message?: TMessage; readonly success: boolean }>;
  /**
   * State keys, at any depth, that must not count as an edit. For state the form carries but does
   * not send: a pending price write is saved through its own call, so editing only a price must not
   * make the form think the entity itself changed.
   */
  readonly transientKeys?: readonly string[];
}

export interface FormApi<TState extends object, TPayload, TMessage = string> {
  /** Reactive form state, bound directly with `v-model="form.state.txRef"`. */
  readonly state: UnwrapNestedRefs<TState>;
  /** Visible messages for a dotted path, e.g. `txRef` or `spend.0.amount`. */
  readonly errors: (path: string) => string[];
  readonly touch: (path: string) => void;
  readonly dirty: ComputedRef<boolean>;
  readonly errorCount: ComputedRef<number>;
  readonly valid: ComputedRef<boolean>;
  readonly submitting: ComputedRef<boolean>;
  readonly reset: (next?: TState) => void;
  /** Backend field errors, keyed by the same dotted paths. Replaces Vuelidate's `$externalResults`. */
  readonly setServerErrors: (errors: Record<string, string[]>) => void;
  /**
   * Reveals every field's errors and reports whether the state parses, without submitting. For save
   * pipelines that have work to do between "the input is good" and "persist it".
   */
  readonly validate: () => boolean;
  readonly submit: () => Promise<FormOutcome<TPayload, TMessage>>;
}

interface PathTarget {
  owner: object;
  key: string;
}

interface ServerError {
  messages: string[];
  /** The value the error was reported against, so it can be dropped once the user edits that field. */
  value: unknown;
}

/**
 * Headless form core with zod as the single validation source of truth.
 *
 * The state is one reactive object that templates bind straight into, so there are no per-field
 * writable computeds to keep in sync and no second copy of the data to reconcile.
 *
 * Errors are keyed by **dotted path** (`spend.0.amount`), which is what lets a form hold arrays of
 * sub-forms: keying by the first path segment alone would collapse every row's errors onto `spend`
 * and every row would show every other row's messages.
 *
 * Touched state is keyed by the **owning object**, not by the path string. Removing the first of
 * three rows shifts every index below it, so index-keyed flags would stay behind and decorate the
 * wrong row; object identity survives a splice, so the flags follow the row. This relies on rows
 * being mutated in place rather than replaced wholesale.
 */
export function useForm<TState extends object, TPayload, TMessage = string>(
  options: FormOptions<TState, TPayload, TMessage>,
): FormApi<TState, TPayload, TMessage> {
  const { t } = useI18n({ useScope: 'global' });

  const state = reactive(options.initial());
  const busy = shallowRef<boolean>(false);
  /** Set once submit runs, so every field shows its errors without having to enumerate the leaves. */
  const submitted = shallowRef<boolean>(false);
  const touched = shallowRef<Map<object, ReadonlySet<string>>>(new Map());
  const server = shallowRef<Map<string, ServerError>>(new Map());

  const transientKeys = new Set(options.transientKeys ?? []);

  /** The state as it is compared for `dirty`, i.e. with the transient keys left out. */
  function serialise(): string {
    return JSON.stringify(state, (key, value) => (transientKeys.has(key) ? undefined : value));
  }

  const snapshot = shallowRef<string>(serialise());

  /** Resolves a dotted path to the object that owns its last segment. */
  function resolve(path: string): PathTarget | undefined {
    const parts = path.split('.');
    const key = parts.pop();
    if (!key)
      return undefined;

    let owner: unknown = state;
    for (const part of parts) {
      if (!isRecord(owner))
        return undefined;
      owner = Reflect.get(owner, part);
    }

    if (!isRecord(owner))
      return undefined;

    return { key, owner };
  }

  function valueAt(path: string): unknown {
    const target = resolve(path);
    if (!target)
      return undefined;
    return Reflect.get(target.owner, target.key);
  }

  function isTouched(path: string): boolean {
    if (get(submitted))
      return true;
    const target = resolve(path);
    if (!target)
      return false;
    return Boolean(get(touched).get(target.owner)?.has(target.key));
  }

  const parsed = computed(() => options.schema.safeParse(state));

  const valid = computed<boolean>(() => get(parsed).success);

  const schemaErrors = computed<Record<string, string[]>>(() => {
    const result = get(parsed);
    if (result.success)
      return {};

    const map: Record<string, string[]> = {};
    for (const issue of result.error.issues) {
      const path = issue.path.map(segment => String(segment)).join('.');
      (map[path] ??= []).push(t(issue.message));
    }
    return map;
  });

  /** A server error survives only until the user edits the field it was reported against. */
  function serverErrors(path: string): string[] {
    const entry = get(server).get(path);
    if (!entry)
      return [];
    return isEqual(valueAt(path), entry.value) ? entry.messages : [];
  }

  function errors(path: string): string[] {
    const schema = isTouched(path) ? get(schemaErrors)[path] ?? [] : [];
    return [...schema, ...serverErrors(path)];
  }

  const errorCount = computed<number>(() => {
    const paths = new Set([...Object.keys(get(schemaErrors)), ...get(server).keys()]);
    let count = 0;
    for (const path of paths) {
      if (errors(path).length > 0)
        count += 1;
    }
    return count;
  });

  const dirty = computed<boolean>(() => serialise() !== get(snapshot));

  function touch(path: string): void {
    const target = resolve(path);
    if (!target)
      return;

    const next = new Map(get(touched));
    const keys = new Set(next.get(target.owner) ?? []);
    keys.add(target.key);
    next.set(target.owner, keys);
    set(touched, next);
  }

  function setServerErrors(errorMessages: Record<string, string[]>): void {
    const next = new Map<string, ServerError>();
    for (const [path, messages] of Object.entries(errorMessages)) {
      if (messages.length > 0)
        next.set(path, { messages, value: valueAt(path) });
    }
    set(server, next);
  }

  function replaceState(next: TState): void {
    for (const key of Object.keys(state))
      Reflect.deleteProperty(state, key);
    Object.assign(state, next);
  }

  function reset(next?: TState): void {
    replaceState(next ?? options.initial());
    set(touched, new Map());
    set(server, new Map());
    set(submitted, false);
    set(snapshot, serialise());
  }

  function validate(): boolean {
    set(submitted, true);
    return get(parsed).success;
  }

  async function submit(): Promise<FormOutcome<TPayload, TMessage>> {
    if (!validate())
      return { outcome: 'invalid' };

    const payload = options.transform(state);
    set(busy, true);
    try {
      const status = await options.submit(payload);
      if (!status.success)
        return { message: status.message, outcome: 'error' };

      set(snapshot, serialise());
      return { outcome: 'success', payload };
    }
    finally {
      set(busy, false);
    }
  }

  return {
    dirty,
    errorCount,
    errors,
    reset,
    setServerErrors,
    state,
    submit,
    submitting: computed<boolean>(() => get(busy)),
    touch,
    valid,
    validate,
  };
}
