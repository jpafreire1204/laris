/**
 * Laris - Aplicação Principal
 * Conversor de artigos científicos em áudio.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { Steps } from './components/Steps';
import { UploadCard } from './components/UploadCard';
import { OptionsCard } from './components/OptionsCard';
import { GenerateCard } from './components/GenerateCard';
import { Alert } from './components/Alert';
import { useApi, Voice, JobStatus, ExtractResponse } from './hooks/useApi';

function App() {
  // Acessibilidade
  const [fontSize, setFontSize] = useState(18);
  const [contrast, setContrast] = useState<'normal' | 'super'>('normal');

  // Estado do fluxo
  const [currentStep, setCurrentStep] = useState(1);

  // Dados extraídos
  const [extractedData, setExtractedData] = useState<ExtractResponse | null>(null);
  const [translatedText, setTranslatedText] = useState<string | null>(null);

  // Configurações
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState('pt-BR-FranciscaNeural');
  const [speed, setSpeed] = useState(1.0);
  const [needsTranslation, setNeedsTranslation] = useState(true);
  const [translationComplete, setTranslationComplete] = useState(false);

  // Status do job
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [textUrl, setTextUrl] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  // API
  const {
    loading,
    error,
    setError,
    extractText,
    translateText,
    getVoices,
    generateAudio,
    checkJobStatus,
  } = useApi();

  // Carrega vozes ao iniciar
  useEffect(() => {
    getVoices().then(setVoices);
  }, [getVoices]);

  // Aplica tamanho de fonte
  useEffect(() => {
    document.documentElement.style.setProperty('--font-size-base', `${fontSize}px`);
    document.documentElement.style.setProperty('--font-size-lg', `${fontSize + 4}px`);
    document.documentElement.style.setProperty('--font-size-xl', `${fontSize + 10}px`);
    document.documentElement.style.setProperty('--font-size-xxl', `${fontSize + 18}px`);
    document.documentElement.style.setProperty('--font-size-sm', `${fontSize - 2}px`);
  }, [fontSize]);

  // Aplica contraste
  useEffect(() => {
    document.documentElement.setAttribute('data-contrast', contrast);
  }, [contrast]);

  // Atalhos de teclado
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey) {
        switch (e.key.toLowerCase()) {
          case 'u':
            e.preventDefault();
            document.querySelector<HTMLElement>('.upload-area')?.click();
            break;
          case 'g':
            e.preventDefault();
            if (currentStep >= 2) {
              handleGenerate();
            }
            break;
          case 'd':
            e.preventDefault();
            if (audioUrl) {
              window.open(audioUrl, '_blank');
            }
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentStep, audioUrl]);

  // Polling do status do job
  useEffect(() => {
    if (!jobStatus || jobStatus.status === 'completed' || jobStatus.status === 'error') {
      return;
    }

    const interval = setInterval(async () => {
      const status = await checkJobStatus(jobStatus.job_id);
      if (status) {
        setJobStatus(status);

        if (status.status === 'completed') {
          setAudioUrl(status.audio_url || null);
          setTextUrl(status.text_url || null);
          setPdfUrl(status.pdf_url || null);
          setCurrentStep(3);
        }
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [jobStatus, checkJobStatus]);

  // Handlers
  const handleFileSelect = async (file: File) => {
    setError(null);
    setExtractedData(null);
    setTranslatedText(null);
    setTranslationComplete(false);
    setJobStatus(null);
    setAudioUrl(null);
    setTextUrl(null);
    setPdfUrl(null);

    const data = await extractText(file);

    if (data) {
      setExtractedData(data);
      setNeedsTranslation(!data.is_portuguese);
      setCurrentStep(2);

      // Se já é português, não precisa traduzir
      if (data.is_portuguese) {
        setTranslatedText(data.text);
        setTranslationComplete(true);
      }
    }
  };

  const handleTranslate = async () => {
    if (!extractedData) return;

    const result = await translateText(extractedData.text, extractedData.detected_language);

    if (result && result.translated_text) {
      setTranslatedText(result.translated_text);
      setTranslationComplete(true);
    }
  };

  const handleToggleTranslation = () => {
    if (extractedData) {
      setTranslatedText(extractedData.text);
      setTranslationComplete(true);
      setNeedsTranslation(false);
    }
  };

  const handleGenerate = async () => {
    const textToSpeak = translatedText || extractedData?.text;
    if (!textToSpeak) return;

    setError(null);
    setJobStatus(null);
    setAudioUrl(null);

    const result = await generateAudio(textToSpeak, selectedVoice, speed);

    if (result) {
      setJobStatus({
        job_id: result.job_id,
        status: 'pending',
        progress: 0,
        message: 'Iniciando...',
      });
    }
  };

  const handleReset = () => {
    setCurrentStep(1);
    setExtractedData(null);
    setTranslatedText(null);
    setTranslationComplete(false);
    setNeedsTranslation(true);
    setJobStatus(null);
    setAudioUrl(null);
    setTextUrl(null);
    setPdfUrl(null);
    setError(null);
  };

  return (
    <div className="container">
      <Header
        fontSize={fontSize}
        onFontSizeChange={setFontSize}
        contrast={contrast}
        onContrastChange={setContrast}
      />

      <main id="main-content">
        <Steps currentStep={currentStep} />

        {/* Erro global */}
        {error && (
          <Alert
            type="error"
            message={error}
            onClose={() => setError(null)}
          />
        )}

        {/* Passo 1: Upload */}
        <UploadCard
          onFileSelect={handleFileSelect}
          loading={loading && currentStep === 1}
          disabled={loading}
        />

        {/* Passo 2: Configuração */}
        {extractedData && (
          <OptionsCard
            preview={extractedData.preview}
            charCount={extractedData.char_count}
            detectedLanguage={extractedData.detected_language}
            languageName={extractedData.language_name}
            isPortuguese={extractedData.is_portuguese}
            needsTranslation={needsTranslation}
            onToggleTranslation={handleToggleTranslation}
            translationLoading={loading}
            translationComplete={translationComplete}
            voices={voices}
            selectedVoice={selectedVoice}
            onVoiceChange={setSelectedVoice}
            speed={speed}
            onSpeedChange={setSpeed}
            onTranslate={handleTranslate}
            onGenerate={handleGenerate}
            disabled={loading}
            canGenerate={translationComplete}
          />
        )}

        {/* Passo 3: Gerar */}
        {translationComplete && (
          <GenerateCard
            onGenerate={handleGenerate}
            loading={loading}
            jobStatus={jobStatus}
            audioUrl={audioUrl}
            textUrl={textUrl}
            pdfUrl={pdfUrl}
            disabled={loading || !translationComplete}
          />
        )}

        {/* Botão de recomeçar */}
        {currentStep > 1 && (
          <div style={{ textAlign: 'center', marginTop: 'var(--spacing-xl)' }}>
            <button
              onClick={handleReset}
              className="btn btn-secondary"
              disabled={loading}
            >
              Começar de novo
            </button>
          </div>
        )}

        {/* Footer */}
        <footer style={{
          marginTop: 'var(--spacing-xl)',
          paddingTop: 'var(--spacing-lg)',
          borderTop: '2px solid var(--color-border)',
          textAlign: 'center',
          color: 'var(--color-text-muted)',
        }}>
          <p>
            Laris - Converta artigos em áudio
          </p>
          <p style={{ fontSize: 'var(--font-size-sm)', marginTop: 'var(--spacing-sm)' }}>
            Processamento local. Seus arquivos não são enviados para a internet.
          </p>
          <p style={{ fontSize: 'var(--font-size-sm)', marginTop: 'var(--spacing-xs)' }}>
            * A geração de voz usa Microsoft Edge TTS, que requer conexão com a internet.
          </p>
        </footer>
      </main>
    </div>
  );
}

export default App;
