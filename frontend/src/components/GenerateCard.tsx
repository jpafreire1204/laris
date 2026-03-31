/**
 * Laris - Generate card.
 */

import { JobStatus } from '../hooks/useApi';

interface GenerateCardProps {
  onGenerate: () => void;
  loading: boolean;
  jobStatus: JobStatus | null;
  audioUrl: string | null;
  textUrl: string | null;
  pdfUrl: string | null;
  extractionDiagnostics: Record<string, unknown>;
  extractionWarnings: string[];
  disabled?: boolean;
}

const PIPELINE_STEPS = [
  { id: 'queued', label: '1. Upload recebido' },
  { id: 'extracting', label: '2. Extraindo PDF' },
  { id: 'cleaning', label: '3. Limpando texto' },
  { id: 'segmenting', label: '4. Segmentando' },
  { id: 'generating_audio', label: '5. Gerando audio' },
  { id: 'merging_audio', label: '6. Montando MP3' },
  { id: 'ready', label: '7. Pronto para ouvir' },
];

function asNumber(value: unknown): number | null {
  return typeof value === 'number' ? value : null;
}

export function GenerateCard({
  onGenerate,
  loading,
  jobStatus,
  audioUrl,
  textUrl,
  pdfUrl,
  extractionDiagnostics,
  extractionWarnings,
  disabled,
}: GenerateCardProps) {
  const isProcessing = loading || (jobStatus && jobStatus.status !== 'completed' && jobStatus.status !== 'error');
  const isComplete = jobStatus?.status === 'completed' || !!audioUrl;
  const hasError = jobStatus?.status === 'error';
  const currentStage = jobStatus?.stage || (isComplete ? 'ready' : 'queued');

  const details = jobStatus?.details || {};
  const diagnostics = jobStatus?.diagnostics || {};
  const pages = asNumber(extractionDiagnostics.page_count);
  const estimatedDuration = asNumber(details.estimated_duration_seconds) ?? asNumber(diagnostics.estimated_duration_seconds);
  const actualDuration = asNumber(details.actual_duration_seconds) ?? asNumber(diagnostics.actual_duration_seconds);
  const chunksCompleted = asNumber(details.chunks_completed);
  const chunksTotal = asNumber(details.chunks_total);

  const getStatusMessage = () => {
    if (!jobStatus) {
      return '';
    }
    return jobStatus.message || 'Processando...';
  };

  const renderPipelineSteps = () => (
    <div style={{ marginBottom: 'var(--spacing-lg)' }}>
      {PIPELINE_STEPS.map((step) => {
        const currentIndex = PIPELINE_STEPS.findIndex((item) => item.id === currentStage);
        const stepIndex = PIPELINE_STEPS.findIndex((item) => item.id === step.id);
        const completed = stepIndex < currentIndex || (isComplete && step.id === 'ready');
        const active = step.id === currentStage;

        return (
          <div
            key={step.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--spacing-sm)',
              marginBottom: 'var(--spacing-xs)',
              color: completed ? 'var(--color-success)' : active ? 'var(--color-primary)' : 'var(--color-text-muted)',
              fontWeight: active ? 700 : 500,
            }}
          >
            <span>{completed ? '✓' : active ? '•' : '○'}</span>
            <span>{step.label}</span>
          </div>
        );
      })}
    </div>
  );

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Passo 3: Gerar Audio</h2>
        <p className="card-subtitle">Acompanhe o pipeline completo da leitura do artigo</p>
      </div>

      {!isComplete && !hasError && (
        <button
          onClick={onGenerate}
          disabled={disabled || !!isProcessing}
          className="btn btn-primary btn-large"
          aria-busy={!!isProcessing}
          style={{ marginBottom: 'var(--spacing-lg)' }}
        >
          {isProcessing ? (
            <>
              <span className="spinner" />
              Processando artigo...
            </>
          ) : (
            'Gerar Audio'
          )}
        </button>
      )}

      {(isProcessing || isComplete) && renderPipelineSteps()}

      {isProcessing && jobStatus && (
        <div
          role="progressbar"
          aria-valuenow={jobStatus.progress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Progresso da geracao de audio"
        >
          <div className="progress-container">
            <div className="progress-bar" style={{ width: `${jobStatus.progress}%` }} />
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

      {(estimatedDuration || actualDuration || chunksTotal || pages || extractionWarnings.length > 0) && (
        <div style={{ marginTop: 'var(--spacing-lg)', marginBottom: 'var(--spacing-lg)' }}>
          <h3 style={{ marginBottom: 'var(--spacing-sm)' }}>Resumo do Processamento</h3>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: 'var(--spacing-sm)',
            }}
          >
            {typeof pages === 'number' && <div className="alert">Paginas processadas: {pages}</div>}
            {typeof chunksTotal === 'number' && (
              <div className="alert">
                Chunks: {chunksCompleted ?? 0}/{chunksTotal}
              </div>
            )}
            {typeof estimatedDuration === 'number' && (
              <div className="alert">Duracao estimada: {Math.round(estimatedDuration)} s</div>
            )}
            {typeof actualDuration === 'number' && actualDuration > 0 && (
              <div className="alert">Duracao real: {Math.round(actualDuration)} s</div>
            )}
          </div>
        </div>
      )}

      {(extractionWarnings.length > 0 || (jobStatus?.warnings || []).length > 0) && (
        <div className="alert alert-warning" role="alert" style={{ marginBottom: 'var(--spacing-lg)' }}>
          {[...extractionWarnings, ...(jobStatus?.warnings || [])].join(' ')}
        </div>
      )}

      {hasError && (
        <div style={{ marginBottom: 'var(--spacing-lg)' }}>
          <div className="alert alert-error" role="alert">
            {jobStatus?.error || 'Ocorreu um erro ao gerar o audio.'}
          </div>
          <button onClick={onGenerate} className="btn btn-primary">
            Tentar novamente
          </button>
        </div>
      )}

      {isComplete && audioUrl && (
        <div aria-live="polite">
          <div className="alert alert-success" role="status">
            Audio gerado com sucesso.
          </div>

          <div style={{ marginBottom: 'var(--spacing-lg)' }}>
            <h3 style={{ marginBottom: 'var(--spacing-sm)' }}>Ouvir Aqui</h3>
            <audio
              controls
              className="audio-player"
              src={audioUrl}
              aria-label="Player de audio do texto narrado"
            >
              Seu navegador nao suporta o elemento de audio.
            </audio>
          </div>

          <div
            style={{
              display: 'flex',
              gap: 'var(--spacing-md)',
              flexWrap: 'wrap',
            }}
          >
            <a
              href={audioUrl}
              download
              className="btn btn-success btn-large"
              style={{ flex: 1, minWidth: '250px', textDecoration: 'none' }}
              aria-label="Baixar arquivo de audio MP3"
            >
              Baixar Audio (MP3)
            </a>

            {pdfUrl && (
              <a
                href={pdfUrl}
                download
                className="btn btn-primary btn-large"
                style={{ flex: 1, minWidth: '250px', textDecoration: 'none' }}
                aria-label="Baixar artigo em PDF"
              >
                Baixar Artigo (PDF)
              </a>
            )}

            {textUrl && (
              <a
                href={textUrl}
                download
                className="btn btn-secondary btn-large"
                style={{ flex: 1, minWidth: '250px', textDecoration: 'none' }}
                aria-label="Baixar texto em TXT"
              >
                Baixar Texto (TXT)
              </a>
            )}
          </div>

          <p
            style={{
              marginTop: 'var(--spacing-md)',
              color: 'var(--color-text-muted)',
              fontSize: 'var(--font-size-sm)',
              textAlign: 'center',
            }}
          >
            Atalho para download: Alt + D
          </p>
        </div>
      )}

      {!isComplete && !isProcessing && !hasError && (
        <p
          style={{
            color: 'var(--color-text-muted)',
            fontSize: 'var(--font-size-sm)',
            textAlign: 'center',
            marginTop: 'var(--spacing-md)',
          }}
        >
          Atalho: Alt + G
        </p>
      )}
    </div>
  );
}
