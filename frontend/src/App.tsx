/**
 * Laris - Aplicacao principal.
 */

import { useEffect, useState } from 'react';
import { Alert } from './components/Alert';
import { GenerateCard } from './components/GenerateCard';
import { Header } from './components/Header';
import { OptionsCard } from './components/OptionsCard';
import { Steps } from './components/Steps';
import { UploadCard } from './components/UploadCard';
import { ExtractResponse, JobStatus, Voice, useApi } from './hooks/useApi';

function App() {
  const [fontSize, setFontSize] = useState(18);
  const [contrast, setContrast] = useState<'normal' | 'super'>('normal');
  const [currentStep, setCurrentStep] = useState(1);

  const [extractedData, setExtractedData] = useState<ExtractResponse | null>(null);
  const [translatedText, setTranslatedText] = useState<string | null>(null);
  const [uploadedFilename, setUploadedFilename] = useState('');

  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState('pt-BR-FranciscaNeural');
  const [speed, setSpeed] = useState(1.0);
  const [translationComplete, setTranslationComplete] = useState(false);
  const [includeReferences, setIncludeReferences] = useState(false);

  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [textUrl, setTextUrl] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

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

  useEffect(() => {
    getVoices().then(setVoices);
  }, [getVoices]);

  useEffect(() => {
    document.documentElement.style.setProperty('--font-size-base', `${fontSize}px`);
    document.documentElement.style.setProperty('--font-size-lg', `${fontSize + 4}px`);
    document.documentElement.style.setProperty('--font-size-xl', `${fontSize + 10}px`);
    document.documentElement.style.setProperty('--font-size-xxl', `${fontSize + 18}px`);
    document.documentElement.style.setProperty('--font-size-sm', `${fontSize - 2}px`);
  }, [fontSize]);

  useEffect(() => {
    document.documentElement.setAttribute('data-contrast', contrast);
  }, [contrast]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!event.altKey) {
        return;
      }

      switch (event.key.toLowerCase()) {
        case 'u':
          event.preventDefault();
          document.querySelector<HTMLElement>('.upload-area')?.click();
          break;
        case 'g':
          event.preventDefault();
          if (currentStep >= 2) {
            void handleGenerate();
          }
          break;
        case 'd':
          event.preventDefault();
          if (audioUrl) {
            window.open(audioUrl, '_blank');
          }
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentStep, audioUrl]);

  useEffect(() => {
    if (!jobStatus || jobStatus.status === 'completed' || jobStatus.status === 'error') {
      return;
    }

    const interval = setInterval(async () => {
      const status = await checkJobStatus(jobStatus.job_id);
      if (!status) {
        return;
      }

      setJobStatus(status);
      if (status.status === 'completed') {
        setAudioUrl(status.audio_url || null);
        setTextUrl(status.text_url || null);
        setPdfUrl(status.pdf_url || null);
        setCurrentStep(3);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [jobStatus, checkJobStatus]);

  const handleFileSelect = async (file: File) => {
    setError(null);
    setExtractedData(null);
    setTranslatedText(null);
    setUploadedFilename(file.name);
    setTranslationComplete(false);
    setIncludeReferences(false);
    setJobStatus(null);
    setAudioUrl(null);
    setTextUrl(null);
    setPdfUrl(null);

    const data = await extractText(file);
    if (!data) {
      return;
    }

    setExtractedData(data);
    setCurrentStep(2);

    if (data.is_portuguese) {
      setTranslatedText(data.text);
      setTranslationComplete(true);
    }
  };

  const handleTranslate = async () => {
    if (!extractedData) {
      return;
    }

    const result = await translateText(extractedData.text, extractedData.detected_language);
    if (result?.translated_text) {
      setTranslatedText(result.translated_text);
      setTranslationComplete(true);
    }
  };

  const handleToggleTranslation = () => {
    if (!extractedData) {
      return;
    }

    setTranslatedText(extractedData.text);
    setTranslationComplete(true);
  };

  const handleGenerate = async () => {
    const textToSpeak = translatedText || extractedData?.text;
    if (!textToSpeak) {
      return;
    }

    setError(null);
    setJobStatus(null);
    setAudioUrl(null);

    const result = await generateAudio(
      textToSpeak,
      selectedVoice,
      speed,
      extractedData?.file_id,
      true,
      uploadedFilename,
      includeReferences
    );

    if (result) {
      setJobStatus({
        job_id: result.job_id,
        status: 'pending',
        progress: 0,
        message: 'Upload recebido',
        stage: 'queued',
        details: {},
        diagnostics: {},
        warnings: [],
      });
    }
  };

  const handleReset = () => {
    setCurrentStep(1);
    setExtractedData(null);
    setTranslatedText(null);
    setUploadedFilename('');
    setTranslationComplete(false);
    setIncludeReferences(false);
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

        {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

        <UploadCard
          onFileSelect={handleFileSelect}
          loading={loading && currentStep === 1}
          disabled={loading}
        />

        {extractedData && (
          <OptionsCard
            preview={extractedData.preview}
            charCount={extractedData.char_count}
            detectedLanguage={extractedData.detected_language}
            languageName={extractedData.language_name}
            isPortuguese={extractedData.is_portuguese}
            onToggleTranslation={handleToggleTranslation}
            translationLoading={loading}
            translationComplete={translationComplete}
            voices={voices}
            selectedVoice={selectedVoice}
            onVoiceChange={setSelectedVoice}
            speed={speed}
            onSpeedChange={setSpeed}
            includeReferences={includeReferences}
            onIncludeReferencesChange={setIncludeReferences}
            extractionDiagnostics={extractedData.diagnostics || {}}
            extractionWarnings={extractedData.warnings || []}
            onTranslate={handleTranslate}
            onGenerate={handleGenerate}
            disabled={loading}
            canGenerate={translationComplete}
          />
        )}

        {translationComplete && (
          <GenerateCard
            onGenerate={handleGenerate}
            loading={loading}
            jobStatus={jobStatus}
            audioUrl={audioUrl}
            textUrl={textUrl}
            pdfUrl={pdfUrl}
            extractionDiagnostics={extractedData?.diagnostics || {}}
            extractionWarnings={extractedData?.warnings || []}
            disabled={loading || !translationComplete}
          />
        )}

        {currentStep > 1 && (
          <div style={{ textAlign: 'center', marginTop: 'var(--spacing-xl)' }}>
            <button onClick={handleReset} className="btn btn-secondary" disabled={loading}>
              Comecar de novo
            </button>
          </div>
        )}

        <footer
          style={{
            marginTop: 'var(--spacing-xl)',
            paddingTop: 'var(--spacing-lg)',
            borderTop: '2px solid var(--color-border)',
            textAlign: 'center',
            color: 'var(--color-text-muted)',
          }}
        >
          <p>Laris - Converta artigos em audio</p>
          <p style={{ fontSize: 'var(--font-size-sm)', marginTop: 'var(--spacing-sm)' }}>
            Processamento local. Seus arquivos nao sao enviados para a internet.
          </p>
          <p style={{ fontSize: 'var(--font-size-sm)', marginTop: 'var(--spacing-xs)' }}>
            * A geracao de voz usa Microsoft Edge TTS, que requer conexao com a internet.
          </p>
        </footer>
      </main>
    </div>
  );
}

export default App;
