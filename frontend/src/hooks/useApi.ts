/**
 * Laris - API Hook
 * Hook para comunicação com o backend.
 */

import { useState, useCallback } from 'react';

const API_BASE = '/api';

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

// Hook principal
export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Extrai texto de arquivo
  const extractText = useCallback(async (file: File): Promise<ExtractResponse | null> => {
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/extract`, {
        method: 'POST',
        body: formData,
      });

      const data: ExtractResponse = await response.json();

      if (!data.success) {
        setError(data.error || 'Erro ao extrair texto');
        return null;
      }

      return data;
    } catch (err) {
      setError('Erro de conexão. Verifique se o servidor está rodando.');
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
      const response = await fetch(`${API_BASE}/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          source_language: sourceLanguage,
        }),
      });

      const data: TranslateResponse = await response.json();

      if (!data.success) {
        setError(data.error || 'Erro na tradução');
        return null;
      }

      return data;
    } catch (err) {
      setError('Erro de conexão ao traduzir.');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Lista vozes disponíveis
  const getVoices = useCallback(async (): Promise<Voice[]> => {
    try {
      const response = await fetch(`${API_BASE}/voices`);
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

    try {
      const response = await fetch(`${API_BASE}/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          voice_id: voiceId,
          speed,
        }),
      });

      const data: TTSResponse = await response.json();

      if (!data.success) {
        setError(data.error || 'Erro ao gerar áudio');
        return null;
      }

      return data;
    } catch (err) {
      setError('Erro de conexão ao gerar áudio.');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Verifica status do job
  const checkJobStatus = useCallback(async (jobId: string): Promise<JobStatus | null> => {
    try {
      const response = await fetch(`${API_BASE}/tts/status/${jobId}`);
      return await response.json();
    } catch {
      return null;
    }
  }, []);

  // Verifica status dos pacotes de tradução
  const checkTranslationStatus = useCallback(async (): Promise<TranslationStatus | null> => {
    try {
      const response = await fetch(`${API_BASE}/translate/status`);
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
      const response = await fetch(`${API_BASE}/translate/install`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from_code: fromCode,
          to_code: toCode,
        }),
      });

      const data = await response.json();

      if (!data.success) {
        setError(data.error || 'Erro ao instalar pacote');
        return false;
      }

      return true;
    } catch (err) {
      setError('Erro de conexão ao instalar pacote.');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    setError,
    extractText,
    translateText,
    getVoices,
    generateAudio,
    checkJobStatus,
    checkTranslationStatus,
    installTranslationPackage,
  };
}
