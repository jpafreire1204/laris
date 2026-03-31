/**
 * Laris - Local TTS Hook
 * Síntese de voz no navegador via Web Speech API.
 * Chrome/Edge expõem as vozes Microsoft Neural PT-BR nativamente.
 */

import { useState, useCallback, useRef } from 'react';
import type { Voice } from './useApi';

const FEMININE_HINTS = ['francisca', 'thalita', 'brenda', 'elza', 'leila', 'vitória', 'vitoria',
  'ana', 'maria', 'camila', 'female', 'feminino', 'zira', 'hazel', 'helena'];
const MASCULINE_HINTS = ['antonio', 'antônio', 'donato', 'leandro', 'daniel', 'paulo', 'ricardo',
  'male', 'masculino', 'david', 'mark', 'jorge'];

function detectGender(voiceName: string): 'Feminino' | 'Masculino' {
  const lower = voiceName.toLowerCase();
  if (MASCULINE_HINTS.some(h => lower.includes(h))) return 'Masculino';
  if (FEMININE_HINTS.some(h => lower.includes(h))) return 'Feminino';
  return 'Feminino';
}

function cleanVoiceName(name: string): string {
  return name
    .replace(/Microsoft\s+/gi, '')
    .replace(/\s+Online\s*\(Natural\)/gi, '')
    .replace(/\s+Online/gi, '')
    .replace(/\s+\(.*?\)/g, '')
    .replace(/Google\s+/gi, '')
    .trim() || name;
}

function splitTextIntoChunks(text: string, maxLen = 2500): string[] {
  if (text.length <= maxLen) return [text];

  const chunks: string[] = [];
  let remaining = text;

  while (remaining.length > 0) {
    if (remaining.length <= maxLen) {
      chunks.push(remaining);
      break;
    }

    // Prefere quebrar no final de sentença
    let splitAt = remaining.lastIndexOf('. ', maxLen);
    if (splitAt < maxLen * 0.5) splitAt = remaining.lastIndexOf('\n', maxLen);
    if (splitAt < maxLen * 0.3) splitAt = remaining.lastIndexOf(' ', maxLen);
    if (splitAt < 0) splitAt = maxLen;

    chunks.push(remaining.slice(0, splitAt + 1).trim());
    remaining = remaining.slice(splitAt + 1).trim();
  }

  return chunks.filter(c => c.length > 0);
}

export type TTSStatus = 'idle' | 'speaking' | 'paused' | 'done' | 'error';

export function useLocalTTS() {
  const [status, setStatus] = useState<TTSStatus>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const chunksRef = useRef<string[]>([]);
  const currentChunkRef = useRef(0);
  const selectedVoiceRef = useRef<SpeechSynthesisVoice | null>(null);
  const speedRef = useRef(1);
  const stoppedRef = useRef(false);

  const getVoices = useCallback((): Promise<Voice[]> => {
    return new Promise((resolve) => {
      if (!('speechSynthesis' in window)) {
        resolve([]);
        return;
      }

      const synth = window.speechSynthesis;

      const mapVoices = () => {
        const all = synth.getVoices();
        const ptVoices = all.filter(v => v.lang.startsWith('pt'));

        if (ptVoices.length === 0) {
          // Fallback: aceita qualquer voz disponível
          resolve(all.slice(0, 6).map(v => ({
            id: v.voiceURI,
            name: cleanVoiceName(v.name),
            gender: detectGender(v.name),
            locale: v.lang,
          })));
          return;
        }

        resolve(ptVoices.map(v => ({
          id: v.voiceURI,
          name: cleanVoiceName(v.name),
          gender: detectGender(v.name),
          locale: v.lang,
        })));
      };

      if (synth.getVoices().length > 0) {
        mapVoices();
      } else {
        synth.addEventListener('voiceschanged', mapVoices, { once: true });
        // Fallback timeout caso o evento não dispare
        setTimeout(mapVoices, 1500);
      }
    });
  }, []);

  const speakChunk = useCallback((index: number) => {
    if (stoppedRef.current) return;

    const synth = window.speechSynthesis;
    const chunks = chunksRef.current;

    if (index >= chunks.length) {
      setStatus('done');
      setProgress(100);
      return;
    }

    const utterance = new SpeechSynthesisUtterance(chunks[index]);
    utterance.rate = speedRef.current;
    utterance.lang = 'pt-BR';

    if (selectedVoiceRef.current) {
      utterance.voice = selectedVoiceRef.current;
    }

    utterance.onstart = () => {
      currentChunkRef.current = index;
      setProgress(Math.round(((index + 1) / chunks.length) * 100));
    };

    utterance.onend = () => {
      if (stoppedRef.current) return;
      speakChunk(index + 1);
    };

    utterance.onerror = (e) => {
      if (e.error === 'interrupted' || e.error === 'canceled') return;
      setStatus('error');
      setError(`Erro na síntese de voz: ${e.error}`);
    };

    synth.speak(utterance);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const speak = useCallback((text: string, voiceId: string, speed: number) => {
    if (!('speechSynthesis' in window)) {
      setError('Seu navegador não suporta síntese de voz.');
      setStatus('error');
      return;
    }

    const synth = window.speechSynthesis;
    synth.cancel();
    stoppedRef.current = false;

    const allVoices = synth.getVoices();
    selectedVoiceRef.current = allVoices.find(v => v.voiceURI === voiceId) ?? null;
    speedRef.current = speed;

    const chunks = splitTextIntoChunks(text);
    chunksRef.current = chunks;
    currentChunkRef.current = 0;

    setStatus('speaking');
    setProgress(0);
    setError(null);

    speakChunk(0);
  }, [speakChunk]);

  const pause = useCallback(() => {
    window.speechSynthesis?.pause();
    setStatus('paused');
  }, []);

  const resume = useCallback(() => {
    window.speechSynthesis?.resume();
    setStatus('speaking');
  }, []);

  const stop = useCallback(() => {
    stoppedRef.current = true;
    window.speechSynthesis?.cancel();
    setStatus('idle');
    setProgress(0);
    currentChunkRef.current = 0;
  }, []);

  const resetError = useCallback(() => {
    setError(null);
    setStatus('idle');
  }, []);

  return { status, progress, error, getVoices, speak, pause, resume, stop, resetError };
}
