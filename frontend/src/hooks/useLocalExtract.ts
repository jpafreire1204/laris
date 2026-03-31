/**
 * Laris - Local Extract Hook
 * Extração de texto no navegador, sem servidor.
 * PDF: pdfjs-dist | DOCX: mammoth | TXT: FileReader
 */

import { useState, useCallback } from 'react';
import type { ExtractResponse } from './useApi';

function detectLanguage(text: string): { code: string; name: string; isPortuguese: boolean } {
  const sample = text.slice(0, 2000).toLowerCase();
  const ptWords = ['que', 'de', 'em', 'para', 'uma', 'com', 'por', 'não', 'se', 'do', 'da', 'os', 'as'];
  const ptCount = ptWords.filter(w => sample.includes(` ${w} `)).length;
  if (ptCount >= 4) return { code: 'pt', name: 'Português', isPortuguese: true };

  const enWords = ['the', 'of', 'and', 'to', 'in', 'is', 'it', 'you', 'that', 'was'];
  const enCount = enWords.filter(w => sample.includes(` ${w} `)).length;
  if (enCount >= 4) return { code: 'en', name: 'Inglês', isPortuguese: false };

  return { code: 'unknown', name: 'Desconhecido', isPortuguese: false };
}

function getPreview(text: string, maxLen = 1500): string {
  if (text.length <= maxLen) return text;
  const truncated = text.slice(0, maxLen);
  const lastPeriod = truncated.lastIndexOf('.');
  return lastPeriod > maxLen * 0.6 ? truncated.slice(0, lastPeriod + 1) : truncated + '...';
}

async function extractFromPdf(file: File): Promise<string> {
  const pdfjs = await import('pdfjs-dist');
  // Vite resolve the worker URL at build time
  pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url
  ).href;

  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;
  const pages: string[] = [];

  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    const pageText = content.items
      .map(item => ('str' in item ? item.str : ''))
      .join(' ');
    pages.push(pageText);
  }

  return pages.join('\n\n');
}

async function extractFromDocx(file: File): Promise<string> {
  const mammoth = await import('mammoth');
  const arrayBuffer = await file.arrayBuffer();
  const result = await mammoth.extractRawText({ arrayBuffer });
  return result.value;
}

export function useLocalExtract() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const extractText = useCallback(async (file: File): Promise<ExtractResponse | null> => {
    setLoading(true);
    setError(null);

    try {
      const ext = file.name.toLowerCase().split('.').pop();
      let text = '';

      if (ext === 'pdf' || file.type === 'application/pdf') {
        text = await extractFromPdf(file);
      } else if (ext === 'docx' || file.type.includes('wordprocessingml')) {
        text = await extractFromDocx(file);
      } else {
        text = await file.text();
      }

      // Normaliza espaços e quebras de linha
      text = text
        .replace(/[ \t]+/g, ' ')
        .replace(/\n{3,}/g, '\n\n')
        .trim();

      if (!text || text.length < 10) {
        setError('Não foi possível extrair texto do arquivo.');
        return null;
      }

      const lang = detectLanguage(text);

      return {
        success: true,
        text,
        preview: getPreview(text),
        detected_language: lang.code,
        language_name: lang.name,
        is_portuguese: lang.isPortuguese,
        char_count: text.length,
      };
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Erro ao extrair texto.';
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, setError, extractText };
}
