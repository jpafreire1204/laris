/**
 * Laris - API Hook
 * Hook para comunicacao com o backend.
 */

import { useState, useCallback, useRef } from 'react';

const DEFAULT_API_URL = 'http://localhost:8000';
const rawApiUrl = import.meta.env.VITE_API_URL?.trim();
const normalizedApiUrl = (rawApiUrl || DEFAULT_API_URL).replace(/\/+$/, '');
const API_BASE = `${normalizedApiUrl}/api`;

const REQUEST_TIMEOUT = 30000;
const POLL_TIMEOUT = 15000;
const MAX_POLL_TIME = 3600000;
const EXTRACT_TIMEOUT = 10 * 60 * 1000;

function getConnectionErrorMessage() {
  return 'Não foi possível conectar ao servidor local. Verifique se o backend está rodando na porta 8000.';
}

async function parseApiResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const payload = isJson ? await response.json() : null;

  if (!response.ok) {
    const message =
      payload && typeof payload === 'object' && 'error' in payload && typeof payload.error === 'string'
        ? payload.error
        : `Erro na comunicacao com a API (${response.status}).`;

    throw new Error(message);
  }

  return payload as T;
}

// Tipos
export interface ExtractResponse {
  success: boolean;
  text: string;
  preview: string;
  detected_language: string;
  language_name: string;
  is_portuguese: boolean;
  char_count: number;
  error?: string;
  file_id?: string;
  diagnostics?: Record<string, unknown>;
  warnings?: string[];
}

export interface Voice {
  id: string;
  name: string;
  gender: string;
  locale: string;
}

export interface VoicesResponse {
  voices: Voice[];
}

export interface TranslateResponse {
  success: boolean;
  original_text: string;
  translated_text: string;
  source_language: string;
  target_language: string;
  error?: string;
}

export interface TranslationStatus {
  installed: boolean;
  available_languages: string[];
  needs_download: string[];
}

export interface TTSResponse {
  success: boolean;
  job_id: string;
  status: string;
  audio_url?: string;
  text_url?: string;
  error?: string;
}

export type AudioMode = 'single' | 'parts';

export interface JobStatus {
  job_id: string;
  status: 'pending' | 'extracting' | 'translating' | 'generating_audio' | 'completed' | 'error';
  progress: number;
  message: string;
  audio_url?: string;
  audio_mode?: AudioMode;
  text_url?: string;
  pdf_url?: string;
  error?: string;
  stage?: string;
  details?: Record<string, unknown>;
  diagnostics?: Record<string, unknown>;
  warnings?: string[];
}

// Funcao auxiliar para fetch com timeout
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout: number = REQUEST_TIMEOUT
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

// Hook principal
export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollStartTimeRef = useRef<number>(0);

  // Extrai texto de arquivo
  const extractText = useCallback(async (file: File): Promise<ExtractResponse | null> => {
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetchWithTimeout(
        `${API_BASE}/extract`,
        { method: 'POST', body: formData },
        EXTRACT_TIMEOUT
      );

      const data = await parseApiResponse<ExtractResponse>(response);

      if (!data.success) {
        setError(data.error || 'Erro ao extrair texto');
        return null;
      }

      return data;
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        setError('A extracao demorou muito. Para arquivos grandes, aguarde mais tempo e tente novamente.');
      } else {
        setError(getConnectionErrorMessage());
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Traduz texto
  const translateText = useCallback(async (
    text: string,
    sourceLanguage: string
  ): Promise<TranslateResponse | null> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchWithTimeout(
        `${API_BASE}/translate`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, source_language: sourceLanguage }),
        },
        120000
      );

      const data = await parseApiResponse<TranslateResponse>(response);

      if (!data.success) {
        setError(data.error || 'Erro na tradução');
        return null;
      }

      return data;
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        setError('A tradução demorou muito. Tente um texto menor.');
      } else {
        setError(getConnectionErrorMessage());
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Lista vozes disponiveis
  const getVoices = useCallback(async (): Promise<Voice[]> => {
    try {
      const response = await fetchWithTimeout(`${API_BASE}/voices`, {}, 10000);
      const data = await parseApiResponse<VoicesResponse>(response);
      return data.voices || [];
    } catch {
      return [];
    }
  }, []);

  // Gera audio
  const generateAudio = useCallback(async (
    text: string,
    voiceId: string,
    speed: number,
    fileId?: string,
    skipTranslation: boolean = true,
    filename?: string,
    includeReferences: boolean = false
  ): Promise<TTSResponse | null> => {
    setLoading(true);
    setError(null);
    pollStartTimeRef.current = Date.now();

    try {
      const response = await fetchWithTimeout(
        `${API_BASE}/tts`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text,
            voice_id: voiceId,
            speed,
            file_id: fileId,
            skip_translation: skipTranslation,
            filename: filename || '',
            include_references: includeReferences,
          }),
        },
        REQUEST_TIMEOUT
      );

      const data = await parseApiResponse<TTSResponse>(response);

      if (!data.success) {
        setError(data.error || 'Erro ao iniciar geracao de audio');
        setLoading(false);
        return null;
      }

      return data;
    } catch (err) {
      setLoading(false);
      if (err instanceof Error && err.name === 'AbortError') {
        setError('A API demorou para responder. Tente novamente em alguns instantes.');
      } else {
        setError(getConnectionErrorMessage());
      }
      return null;
    }
  }, []);

  // Verifica status do job
  const checkJobStatus = useCallback(async (jobId: string): Promise<JobStatus | null> => {
    try {
      const elapsedPollTime = Date.now() - pollStartTimeRef.current;
      if (pollStartTimeRef.current > 0 && elapsedPollTime > MAX_POLL_TIME) {
        setError('O processamento excedeu o tempo maximo de espera.');
        setLoading(false);
        return {
          job_id: jobId,
          status: 'error',
          progress: 0,
          message: 'Tempo de espera excedido',
          error: 'O processamento excedeu o tempo maximo de espera.'
        };
      }

      const response = await fetchWithTimeout(
        `${API_BASE}/tts/status/${jobId}`,
        {},
        POLL_TIMEOUT
      );

      if (!response.ok) {
        if (response.status === 404) {
          setError('Job nao encontrado. Tente gerar novamente.');
          setLoading(false);
          return null;
        }
        setError(`Erro ao consultar o processamento (${response.status}). Tente novamente.`);
        return null;
      }

      const status = await parseApiResponse<JobStatus>(response);

      if (status.status === 'completed' || status.status === 'error') {
        setLoading(false);
        pollStartTimeRef.current = 0;

        if (status.status === 'error' && status.error) {
          setError(status.error);
        }
      }

      return status;
    } catch (err) {
      console.warn('Erro ao verificar status (polling continua):', err);
      return null;
    }
  }, []);

  // Reseta estado
  const resetState = useCallback(() => {
    setLoading(false);
    setError(null);
    pollStartTimeRef.current = 0;
  }, []);

  return {
    loading,
    error,
    setError,
    resetState,
    extractText,
    translateText,
    getVoices,
    generateAudio,
    checkJobStatus,
  };
}
