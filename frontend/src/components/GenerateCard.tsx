/**
 * Laris - Generate Card Component
 * Card para progresso de geracao e download do audio.
 */

import React from 'react';
import { JobStatus } from '../hooks/useApi';

interface GenerateCardProps {
  onGenerate: () => void;
  loading: boolean;
  jobStatus: JobStatus | null;
  audioUrl: string | null;
  disabled?: boolean;
}

export function GenerateCard({
  onGenerate,
  loading,
  jobStatus,
  audioUrl,
  disabled,
}: GenerateCardProps) {
  const isProcessing = loading || (jobStatus && jobStatus.status !== 'completed' && jobStatus.status !== 'error');
  const isComplete = jobStatus?.status === 'completed' && audioUrl;
  const hasError = jobStatus?.status === 'error';

  const getProgressPercentage = () => {
    if (!jobStatus) return 0;
    return Math.min(Math.max(jobStatus.progress, 0), 100);
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Passo 3: Resultado</h2>
      </div>

      {/* Barra de progresso durante processamento */}
      {isProcessing && (
        <div
          role="progressbar"
          aria-valuenow={getProgressPercentage()}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Progresso"
          style={{ marginBottom: 'var(--spacing-lg)' }}
        >
          <div className="progress-container">
            <div
              className="progress-bar"
              style={{ width: `${getProgressPercentage()}%` }}
            />
          </div>
          <p style={{
            textAlign: 'center',
            color: 'var(--color-text-secondary)',
            marginTop: 'var(--spacing-md)',
            fontWeight: 500,
          }}>
            Processando... {getProgressPercentage()}%
          </p>
        </div>
      )}

      {/* Erro */}
      {hasError && (
        <div style={{ marginBottom: 'var(--spacing-lg)' }}>
          <div className="alert alert-error" role="alert">
            {jobStatus?.error || 'Ocorreu um erro.'}
          </div>
          <button
            onClick={onGenerate}
            className="btn btn-primary"
            disabled={disabled}
          >
            Tentar novamente
          </button>
        </div>
      )}

      {/* Sucesso - Player e Download */}
      {isComplete && audioUrl && (
        <div aria-live="polite">
          <div className="alert alert-success" role="status">
            Pronto!
          </div>

          {/* Player de audio */}
          <div style={{ marginBottom: 'var(--spacing-lg)' }}>
            <audio
              controls
              className="audio-player"
              src={audioUrl}
              aria-label="Player de audio"
            >
              Seu navegador nao suporta o elemento de audio.
            </audio>
          </div>

          {/* Botao de download */}
          <a
            href={audioUrl}
            download
            className="btn btn-success btn-large"
            style={{ width: '100%', textDecoration: 'none', textAlign: 'center' }}
          >
            Baixar MP3
          </a>
        </div>
      )}
    </div>
  );
}
