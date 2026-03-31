/**
 * Laris - Server Warmup Hook
 * Silently pings backend to wake it up and keeps it alive.
 * No UI side effects — purely background.
 */

import { useEffect, useRef, useCallback } from 'react';

const DEFAULT_API_URL = 'http://localhost:8000';
const rawApiUrl = import.meta.env.VITE_API_URL?.trim();
const normalizedApiUrl = (rawApiUrl || DEFAULT_API_URL).replace(/\/+$/, '');
const API_BASE = `${normalizedApiUrl}/api`;

const RETRY_INTERVAL_MS = 5000;
const MAX_WARMUP_TIME_MS = 90000;
const KEEP_ALIVE_INTERVAL_MS = 14 * 60 * 1000; // 14 minutes

export function useServerWarmup() {
  const startTimeRef = useRef<number>(0);
  const warmupRef = useRef<ReturnType<typeof setInterval>>();
  const keepAliveRef = useRef<ReturnType<typeof setInterval>>();
  const mountedRef = useRef(true);

  const ping = useCallback(async (): Promise<boolean> => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);
      const response = await fetch(`${API_BASE}/health`, {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      return response.ok;
    } catch {
      return false;
    }
  }, []);

  const startKeepAlive = useCallback(() => {
    clearInterval(keepAliveRef.current);
    keepAliveRef.current = setInterval(async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000);
        await fetch(`${API_BASE}/health`, { signal: controller.signal });
        clearTimeout(timeoutId);
      } catch {
        console.warn('Keep-alive ping failed');
      }
    }, KEEP_ALIVE_INTERVAL_MS);
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    startTimeRef.current = Date.now();

    async function check() {
      const ok = await ping();
      if (!mountedRef.current) return;

      if (ok) {
        console.info('Backend is ready');
        startKeepAlive();
        return;
      }

      // Backend is cold — retry silently
      console.info('Backend is waking up...');

      warmupRef.current = setInterval(async () => {
        if (!mountedRef.current) return;

        const elapsed = Date.now() - startTimeRef.current;
        if (elapsed > MAX_WARMUP_TIME_MS) {
          clearInterval(warmupRef.current);
          console.warn('Backend warmup timed out after 90s');
          return;
        }

        const success = await ping();
        if (!mountedRef.current) return;

        if (success) {
          clearInterval(warmupRef.current);
          console.info('Backend is ready');
          startKeepAlive();
        }
      }, RETRY_INTERVAL_MS);
    }

    check();

    return () => {
      mountedRef.current = false;
      clearInterval(warmupRef.current);
      clearInterval(keepAliveRef.current);
    };
  }, [ping, startKeepAlive]);
}
