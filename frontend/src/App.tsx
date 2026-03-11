/**
 * Laris - Aplicacao Principal
 * Conversor de texto em audio.
 * Fluxo: Upload -> Configurar Voz -> Gerar Audio -> Baixar MP3
 */

import { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { Steps } from './components/Steps';
import { UploadCard } from './components/UploadCard';
import { OptionsCard } from './components/OptionsCard';
import { GenerateCard } from './components/GenerateCard';
import { Alert } from './components/Alert';
import { useApi, Voice, JobStatus, ExtractResponse } from './hooks/useApi';
import { useServerWarmup } from './hooks/useServerWarmup';

const MAX_POLL_TIME_MS = 600000; // 10 minutos

function App() {
  const [fontSize, setFontSize] = useState(18);
  const [contrast, setContrast] = useState<'normal' | 'super'>('normal');
  const [currentStep, setCurrentStep] = useState(1);
  const [extractedData, setExtractedData] = useState<ExtractResponse | null>(null);
  const [currentText, setCurrentText] = useState<string>('');
  const [currentPreview, setCurrentPreview] = useState<string>('');
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState('pt-BR-FranciscaNeural');
  const [speed, setSpeed] = useState(1.0);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [fileName, setFileName] = useState('');
  const pollStartTimeRef = useRef<number>(0);
  const userInteractedRef = useRef(false);

  const {
    loading,
    error,
    setError,
    resetState,
    extractText,
    getVoices,
    generateAudio,
    checkJobStatus,
  } = useApi();

  useServerWarmup();

  useEffect(() => {
    getVoices().then(setVoices).catch(() => {});
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
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey) {
        switch (e.key.toLowerCase()) {
          case 'u':
            e.preventDefault();
            document.querySelector<HTMLElement>('.upload-area')?.click();
            break;
          case 'g':
            e.preventDefault();
            if (currentStep >= 2 && !loading && currentText) {
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
  }, [currentStep, audioUrl, loading, currentText]);

  // Polling do status
  useEffect(() => {
    if (!jobStatus) return;

    if (jobStatus.status === 'completed' || jobStatus.status === 'error') {
      pollStartTimeRef.current = 0;
      return;
    }

    if (pollStartTimeRef.current === 0) {
      pollStartTimeRef.current = Date.now();
    }

    const interval = setInterval(async () => {
      const elapsed = Date.now() - pollStartTimeRef.current;
      if (elapsed > MAX_POLL_TIME_MS) {
        setJobStatus({
          ...jobStatus,
          status: 'error',
          error: 'Tempo limite excedido.',
          message: 'Erro'
        });
        setError('Tempo limite excedido.');
        resetState();
        pollStartTimeRef.current = 0;
        return;
      }

      try {
        const status = await checkJobStatus(jobStatus.job_id);

        if (status) {
          setJobStatus(status);

          if (status.status === 'completed') {
            setAudioUrl(status.audio_url || null);
            setCurrentStep(3);
            pollStartTimeRef.current = 0;
          } else if (status.status === 'error') {
            pollStartTimeRef.current = 0;
            if (status.error) {
              setError(status.error);
            }
          }
        } else {
          // Job nao encontrado (404) — para o polling
          setJobStatus({
            ...jobStatus,
            status: 'error',
            error: 'Job perdido. Tente gerar novamente.',
            message: 'Erro'
          });
          pollStartTimeRef.current = 0;
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [jobStatus, checkJobStatus, setError, resetState]);

  const handleFileSelect = async (file: File) => {
    userInteractedRef.current = true;
    setError(null);
    setExtractedData(null);
    setCurrentText('');
    setCurrentPreview('');
    setJobStatus(null);
    setAudioUrl(null);
    pollStartTimeRef.current = 0;

    const nameWithoutExt = file.name.replace(/\.[^/.]+$/, '');
    setFileName(nameWithoutExt);

    const data = await extractText(file);

    if (data) {
      setExtractedData(data);
      setCurrentText(data.text);
      setCurrentPreview(data.preview);
      setCurrentStep(2);
    }
  };

  const handleGenerate = async () => {
    if (!currentText) return;

    userInteractedRef.current = true;
    setError(null);
    setJobStatus(null);
    setAudioUrl(null);
    pollStartTimeRef.current = 0;

    const result = await generateAudio(
      currentText,
      selectedVoice,
      speed,
      extractedData?.file_id,
      true,
      fileName
    );

    if (result && result.job_id) {
      pollStartTimeRef.current = Date.now();
      setJobStatus({
        job_id: result.job_id,
        status: 'pending',
        progress: 0,
        message: 'Processando...',
      });
    }
  };

  const handleReset = () => {
    setCurrentStep(1);
    setExtractedData(null);
    setCurrentText('');
    setCurrentPreview('');
    setJobStatus(null);
    setAudioUrl(null);
    setError(null);
    resetState();
    pollStartTimeRef.current = 0;
  };

  const handleCloseError = () => {
    setError(null);
    if (jobStatus?.status === 'error') {
      setJobStatus(null);
    }
  };

  const isProcessing = jobStatus && jobStatus.status !== 'completed' && jobStatus.status !== 'error';

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

        {error && userInteractedRef.current && (
          <Alert
            type="error"
            message={error}
            onClose={handleCloseError}
          />
        )}

        <UploadCard
          onFileSelect={handleFileSelect}
          loading={loading && currentStep === 1}
          disabled={loading || !!isProcessing}
        />

        {extractedData && !isProcessing && !audioUrl && (
          <OptionsCard
            preview={currentPreview}
            charCount={currentText.length}
            voices={voices}
            selectedVoice={selectedVoice}
            onVoiceChange={setSelectedVoice}
            speed={speed}
            onSpeedChange={setSpeed}
            onGenerate={handleGenerate}
            disabled={loading}
          />
        )}

        {(isProcessing || audioUrl) && (
          <GenerateCard
            onGenerate={handleGenerate}
            loading={loading || isProcessing === true}
            jobStatus={jobStatus}
            audioUrl={audioUrl}
            disabled={loading || isProcessing === true}
          />
        )}

        {currentStep > 1 && !isProcessing && (
          <div style={{ textAlign: 'center', marginTop: 'var(--spacing-xl)' }}>
            <button
              onClick={handleReset}
              className="btn btn-secondary"
              disabled={loading || !!isProcessing}
            >
              Comecar de novo
            </button>
          </div>
        )}

        <footer style={{
          marginTop: 'var(--spacing-xl)',
          paddingTop: 'var(--spacing-lg)',
          borderTop: '2px solid var(--color-border)',
          textAlign: 'center',
          color: 'var(--color-text-muted)',
        }}>
          <p>
            <a
              href="https://www.laris.com.br"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: 'var(--color-primary)',
                textDecoration: 'none',
                fontWeight: 600,
              }}
            >
              www.laris.com.br
            </a>
            {' '}- Converta textos em audio
          </p>
        </footer>
      </main>
    </div>
  );
}

export default App;
