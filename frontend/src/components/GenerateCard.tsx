/**
 * Laris - Generate Card Component
 * Card para geração de áudio e download.
 */

import React from 'react';
import { JobStatus } from '../hooks/useApi';

interface GenerateCardProps {
  onGenerate: () => void;
  loading: boolean;
  jobStatus: JobStatus | null;
  audioUrl: string | null;
  textUrl: string | null;
  pdfUrl: string | null;
  disabled?: boolean;
}

export function GenerateCard({
  onGenerate,
  loading,
  jobStatus,
  audioUrl,
  textUrl,
  pdfUrl,
  disabled,
}: GenerateCardProps) {
  const isProcessing = loading || (jobStatus && jobStatus.status !== 'completed' && jobStatus.status !== 'error');
  const isComplete = jobStatus?.status === 'completed' || audioUrl;
  const hasError = jobStatus?.status === 'error';

  const getStatusMessage = () => {
    if (!jobStatus) return '';

    switch (jobStatus.status) {
      case 'pending':
        return 'Preparando...';
      case 'extracting':
        return 'Extraindo texto...';
      case 'translating':
        return 'Traduzindo texto...';
      case 'generating_audio':
        return 'Gerando áudio... Isso pode levar alguns segundos.';
      case 'completed':
        return 'Áudio gerado com sucesso!';
      case 'error':
        return jobStatus.error || 'Ocorreu um erro.';
      default:
        return jobStatus.message;
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Passo 3: Gerar Áudio</h2>
        <p className="card-subtitle">
          Clique para gerar a narração do texto
        </p>
      </div>

      {/* Botão de gerar */}
      {!isComplete && !hasError && (
        <button
          onClick={onGenerate}
          disabled={disabled || isProcessing}
          className="btn btn-primary btn-large"
          aria-busy={isProcessing}
          style={{ marginBottom: 'var(--spacing-lg)' }}
        >
          {isProcessing ? (
            <>
              <span className="spinner" />
              Gerando áudio...
            </>
          ) : (
            <>
              🔊 Gerar Áudio
            </>
          )}
        </button>
      )}

      {/* Barra de progresso */}
      {isProcessing && jobStatus && (
        <div
          role="progressbar"
          aria-valuenow={jobStatus.progress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Progresso da geração de áudio"
        >
          <div className="progress-container">
            <div
              className="progress-bar"
              style={{ width: `${jobStatus.progress}%` }}
            />
          </div>
          <p
            aria-live="polite"
            style={{
              textAlign: 'center',
              color: 'var(--color-text-secondary)',
              marginTop: 'var(--spacing-sm)',
            }}
          >
            {getStatusMessage()}
          </p>
        </div>
      )}

      {/* Erro */}
      {hasError && (
        <div style={{ marginBottom: 'var(--spacing-lg)' }}>
          <div className="alert alert-error" role="alert">
            {jobStatus?.error || 'Ocorreu um erro ao gerar o áudio.'}
          </div>
          <button
            onClick={onGenerate}
            className="btn btn-primary"
          >
            Tentar novamente
          </button>
        </div>
      )}

      {/* Sucesso - Player e Downloads */}
      {isComplete && audioUrl && (
        <div aria-live="polite">
          <div className="alert alert-success" role="status">
            {jobStatus?.audio_mode === 'parts'
              ? 'Áudio gerado em partes! Baixe o ZIP para ouvir.'
              : 'Áudio gerado com sucesso!'}
          </div>

          {/* Player de áudio - só mostra para MP3 único */}
          {jobStatus?.audio_mode !== 'parts' && (
            <div style={{ marginBottom: 'var(--spacing-lg)' }}>
              <h3 style={{ marginBottom: 'var(--spacing-sm)' }}>Ouvir Aqui</h3>
              <audio
                controls
                className="audio-player"
                src={audioUrl}
                aria-label="Player de áudio do texto narrado"
              >
                Seu navegador não suporta o elemento de áudio.
              </audio>
            </div>
          )}

          {/* Aviso sobre partes */}
          {jobStatus?.audio_mode === 'parts' && (
            <div style={{
              marginBottom: 'var(--spacing-lg)',
              padding: 'var(--spacing-md)',
              backgroundColor: 'var(--color-warning-bg)',
              borderRadius: 'var(--radius-md)',
              border: '2px solid var(--color-warning)',
            }}>
              <p style={{ fontWeight: 600, marginBottom: 'var(--spacing-sm)' }}>
                Texto muito longo
              </p>
              <p style={{ fontSize: 'var(--font-size-sm)' }}>
                O áudio foi dividido em partes. Baixe o ZIP e extraia os arquivos
                para ouvir na ordem (parte_01.mp3, parte_02.mp3, etc.).
              </p>
            </div>
          )}

          {/* Botões de download */}
          <div style={{
            display: 'flex',
            gap: 'var(--spacing-md)',
            flexWrap: 'wrap',
          }}>
            <a
              href={audioUrl}
              download
              className="btn btn-success btn-large"
              style={{ flex: 1, minWidth: '250px', textDecoration: 'none' }}
              aria-label={jobStatus?.audio_mode === 'parts'
                ? 'Baixar arquivo ZIP com partes do áudio'
                : 'Baixar arquivo de áudio MP3'}
            >
              {jobStatus?.audio_mode === 'parts'
                ? '⬇️ Baixar Áudio (ZIP)'
                : '⬇️ Baixar Áudio (MP3)'}
            </a>

            {pdfUrl && (
              <a
                href={pdfUrl}
                download
                className="btn btn-primary btn-large"
                style={{ flex: 1, minWidth: '250px', textDecoration: 'none' }}
                aria-label="Baixar artigo traduzido em formato PDF"
              >
                📕 Baixar Artigo (PDF)
              </a>
            )}

            {textUrl && (
              <a
                href={textUrl}
                download
                className="btn btn-secondary btn-large"
                style={{ flex: 1, minWidth: '250px', textDecoration: 'none' }}
                aria-label="Baixar texto traduzido em formato TXT"
              >
                📄 Baixar Texto (TXT)
              </a>
            )}
          </div>

          <p style={{
            marginTop: 'var(--spacing-md)',
            color: 'var(--color-text-muted)',
            fontSize: 'var(--font-size-sm)',
            textAlign: 'center',
          }}>
            Atalho para download: Alt + D
          </p>
        </div>
      )}

      {/* Dica */}
      {!isComplete && !isProcessing && !hasError && (
        <p style={{
          color: 'var(--color-text-muted)',
          fontSize: 'var(--font-size-sm)',
          textAlign: 'center',
          marginTop: 'var(--spacing-md)',
        }}>
          Atalho: Alt + G
        </p>
      )}
    </div>
  );
}
