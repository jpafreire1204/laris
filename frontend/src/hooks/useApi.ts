/**
 * Laris - API Hook
 * Hook para comunicação com o backend.
 * Com timeouts e tratamento robusto de erros.
 */

import { useState, useCallback, useRef } from 'react';

const API_BASE = '/api';

// Timeouts
const REQUEST_TIMEOUT = 30000;  // 30s para requisições normais
const POLL_TIMEOUT = 10000;     // 10s para polling de status
const MAX_POLL_TIME = 660000;   // 11 minutos máximo de polling (backend tem 10min timeout)

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
}

export interface TranslateResponse {
  success: boolean;
  original_text: string;
  translated_text: string;
  source_language: string;
  target_language: string;
  error?: string;
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
  status: 'pending' | 'extracting' | 'translating' | 'generating_audio' | 'completed' | 'error';
  progress: number;
  message: string;
  audio_url?: string;
  audio_mode?: AudioMode;
  text_url?: string;
  pdf_url?: string;
  error?: string;
}

export interface TranslationStatus {
  installed: boolean;
  available_languages: string[];
  needs_download: string[];
}

export interface HealthStatus {
  ok: boolean;
  service: string;
  active_jobs: number;
  system: {
    edge_tts_available: boolean;
    pydub_available: boolean;
    ffmpeg_available: boolean;
  };
}

// Função auxiliar para fetch com timeout
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

  // Verifica saúde do backend
  const checkHealth = useCallback(async (): Promise<HealthStatus | null> => {
    try {
      const response = await fetchWithTimeout(`${API_BASE}/health`, {}, 5000);
      if (!response.ok) return null;
      return await response.json();
    } catch {
      return null;
    }
  }, []);

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
        60000  // 60s para upload de arquivo
      );

      const data: ExtractResponse = await response.json();

      if (!data.success) {
        setError(data.error || 'Erro ao extrair texto');
        return null;
      }

      return data;
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        setError('A extração demorou muito. Tente um arquivo menor.');
      } else {
        setError('Erro de conexão. Verifique se o servidor está rodando.');
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
        120000  // 2 minutos para tradução
      );

      const data: TranslateResponse = await response.json();

      if (!data.success) {
        setError(data.error || 'Erro na tradução');
        return null;
      }

      return data;
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        setError('A tradução demorou muito. Tente novamente.');
      } else {
        setError('Erro de conexão ao traduzir.');
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Lista vozes disponíveis
  const getVoices = useCallback(async (): Promise<Voice[]> => {
    try {
      const response = await fetchWithTimeout(`${API_BASE}/voices`, {}, 10000);
      const data: VoicesResponse = await response.json();
      return data.voices || [];
    } catch {
      return [];
    }
  }, []);

  // Gera áudio
  const generateAudio = useCallback(async (
    text: string,
    voiceId: string,
    speed: number
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
          body: JSON.stringify({ text, voice_id: voiceId, speed }),
        },
        REQUEST_TIMEOUT
      );

      const data: TTSResponse = await response.json();

      if (!data.success) {
        setError(data.error || 'Erro ao iniciar geração de áudio');
        setLoading(false);
        return null;
      }

      return data;
    } catch (err) {
      setLoading(false);
      if (err instanceof Error && err.name === 'AbortError') {
        setError('Erro de conexão ao iniciar geração. Tente novamente.');
      } else {
        setError('Erro de conexão ao gerar áudio.');
      }
      return null;
    }
    // Nota: loading continua true para o polling
  }, []);

  // Verifica status do job
  const checkJobStatus = useCallback(async (jobId: string): Promise<JobStatus | null> => {
    try {
      // Verifica tempo máximo de polling
      const elapsedPollTime = Date.now() - pollStartTimeRef.current;
      if (pollStartTimeRef.current > 0 && elapsedPollTime > MAX_POLL_TIME) {
        setError('O processamento demorou muito. Por favor, tente novamente com um texto menor.');
        setLoading(false);
        return {
          job_id: jobId,
          status: 'error',
          progress: 0,
          message: 'Tempo limite excedido',
          error: 'O processamento demorou muito. Por favor, tente novamente.'
        };
      }

      const response = await fetchWithTimeout(
        `${API_BASE}/tts/status/${jobId}`,
        {},
        POLL_TIMEOUT
      );

      if (!response.ok) {
        if (response.status === 404) {
          setError('Job não encontrado. Tente gerar novamente.');
          setLoading(false);
          return null;
        }
        throw new Error(`HTTP ${response.status}`);
      }

      const status: JobStatus = await response.json();

      // Se completou ou erro, para o loading
      if (status.status === 'completed' || status.status === 'error') {
        setLoading(false);
        pollStartTimeRef.current = 0;

        if (status.status === 'error' && status.error) {
          setError(status.error);
        }
      }

      return status;
    } catch (err) {
      // Não seta erro em falhas de polling individual, apenas loga
      console.warn('Erro ao verificar status:', err);
      return null;
    }
  }, []);

  // Verifica status dos pacotes de tradução
  const checkTranslationStatus = useCallback(async (): Promise<TranslationStatus | null> => {
    try {
      const response = await fetchWithTimeout(`${API_BASE}/translate/status`, {}, 10000);
      return await response.json();
    } catch {
      return null;
    }
  }, []);

  // Instala pacote de tradução
  const installTranslationPackage = useCallback(async (
    fromCode: string = 'en',
    toCode: string = 'pt'
  ): Promise<boolean> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchWithTimeout(
        `${API_BASE}/translate/install`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ from_code: fromCode, to_code: toCode }),
        },
        300000  // 5 minutos para instalação
      );

      const data = await response.json();

      if (!data.success) {
        setError(data.error || 'Erro ao instalar pacote');
        return false;
      }

      return true;
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        setError('A instalação demorou muito. Tente novamente.');
      } else {
        setError('Erro de conexão ao instalar pacote.');
      }
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  // Reseta estado de erro e loading
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
    checkHealth,
    extractText,
    translateText,
    getVoices,
    generateAudio,
    checkJobStatus,
    checkTranslationStatus,
    installTranslationPackage,
  };
}
