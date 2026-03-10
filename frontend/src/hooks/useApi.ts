/**
 * Laris - API Hook
 * Hook para comunicacao com o backend.
 */

import { useState, useCallback, useRef } from 'react';

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

const REQUEST_TIMEOUT = 30000;
const POLL_TIMEOUT = 15000;
const MAX_POLL_TIME = 3600000;

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
  status: 'pending' | 'extracting' | 'generating_audio' | 'completed' | 'error';
  progress: number;
  message: string;
  audio_url?: string;
  audio_mode?: AudioMode;
  text_url?: string;
  pdf_url?: string;
  error?: string;
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
        60000
      );

      const data: ExtractResponse = await response.json();

      if (!data.success) {
        setError(data.error || 'Erro ao extrair texto');
        return null;
      }

      return data;
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        setError('A extracao demorou muito. Tente um arquivo menor.');
      } else {
        setError('Erro de conexao. Verifique se o servidor esta rodando.');
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
      const data: VoicesResponse = await response.json();
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
    filename?: string
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
          body: JSON.stringify({ text, voice_id: voiceId, speed, file_id: fileId, skip_translation: skipTranslation, filename: filename || '' }),
        },
        REQUEST_TIMEOUT
      );

      const data: TTSResponse = await response.json();

      if (!data.success) {
        setError(data.error || 'Erro ao iniciar geracao de audio');
        setLoading(false);
        return null;
      }

      return data;
    } catch (err) {
      setLoading(false);
      if (err instanceof Error && err.name === 'AbortError') {
        setError('Erro de conexao ao iniciar geracao. Tente novamente.');
      } else {
        setError('Erro de conexao ao gerar audio.');
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
        return null;
      }

      const status: JobStatus = await response.json();

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
    getVoices,
    generateAudio,
    checkJobStatus,
  };
}
