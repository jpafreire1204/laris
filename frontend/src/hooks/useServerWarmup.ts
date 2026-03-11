/**
 * Laris - Server Warmup Hook
 * Detecta cold start do Render free tier e mostra status amigavel.
 */

import { useState, useEffect, useRef, useCallback } from 'react';

const DEFAULT_API_URL = 'https://laris-api.vercel.app';
const rawApiUrl = import.meta.env.VITE_API_URL?.trim();
const normalizedApiUrl = (rawApiUrl || DEFAULT_API_URL).replace(/\/+$/, '');
const API_BASE = `${normalizedApiUrl}/api`;

const RETRY_INTERVAL_MS = 5000;
const MAX_WARMUP_TIME_MS = 90000;

export type WarmupStatus = 'checking' | 'warming' | 'ready' | 'failed';

export function useServerWarmup() {
  const [status, setStatus] = useState<WarmupStatus>('checking');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [showSuccess, setShowSuccess] = useState(false);
  const startTimeRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setInterval>>();
  const mountedRef = useRef(true);

  const ping = useCallback(async (): Promise<boolean> => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);
      const response = await fetch(`${API_BASE}/voices`, {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      return response.ok;
    } catch {
      return false;
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    startTimeRef.current = Date.now();

    async function check() {
      const ok = await ping();

      if (!mountedRef.current) return;

      if (ok) {
        setStatus('ready');
        return;
      }

      // First ping failed — backend is cold, start retry loop
      setStatus('warming');

      timerRef.current = setInterval(async () => {
        if (!mountedRef.current) return;

        const elapsed = Date.now() - startTimeRef.current;
        setElapsedSeconds(Math.floor(elapsed / 1000));

        if (elapsed > MAX_WARMUP_TIME_MS) {
          clearInterval(timerRef.current);
          if (mountedRef.current) setStatus('failed');
          return;
        }

        const success = await ping();
        if (!mountedRef.current) return;

        if (success) {
          clearInterval(timerRef.current);
          setStatus('ready');
          setShowSuccess(true);
          setTimeout(() => {
            if (mountedRef.current) setShowSuccess(false);
          }, 2000);
        }
      }, RETRY_INTERVAL_MS);
    }

    check();

    // Elapsed seconds counter (updates every second for display)
    const secondsTimer = setInterval(() => {
      if (!mountedRef.current) return;
      const elapsed = Date.now() - startTimeRef.current;
      setElapsedSeconds(Math.floor(elapsed / 1000));
    }, 1000);

    return () => {
      mountedRef.current = false;
      clearInterval(timerRef.current);
      clearInterval(secondsTimer);
    };
  }, [ping]);

  return { status, elapsedSeconds, showSuccess };
}
