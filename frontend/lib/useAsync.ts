"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type AsyncStatus = "idle" | "loading" | "success" | "error";

export interface AsyncState<T> {
  status: AsyncStatus;
  data: T | null;
  error: Error | null;
  /** Re-run the loader; useful for retry buttons. */
  reload: () => void;
  /** Imperatively replace data (e.g. after a mutation). */
  setData: (updater: T | ((prev: T | null) => T)) => void;
}

/**
 * Runs an async loader on mount and whenever `deps` change. Aborts in-flight
 * requests on unmount / reload and never sets state after unmount.
 */
export function useAsync<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  deps: unknown[] = [],
): AsyncState<T> {
  const [status, setStatus] = useState<AsyncStatus>("loading");
  const [data, setDataState] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [nonce, setNonce] = useState(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading");
    setError(null);
    loader(controller.signal)
      .then((result) => {
        if (!mounted.current || controller.signal.aborted) return;
        setDataState(result);
        setStatus("success");
      })
      .catch((err: Error) => {
        if (!mounted.current || controller.signal.aborted) return;
        if (err.name === "AbortError") return;
        setError(err);
        setStatus("error");
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  const setData = useCallback((updater: T | ((prev: T | null) => T)) => {
    setDataState((prev) =>
      typeof updater === "function"
        ? (updater as (p: T | null) => T)(prev)
        : updater,
    );
  }, []);

  return { status, data, error, reload, setData };
}
