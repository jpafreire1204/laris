/**
 * Laris - Options card.
 */

import { Voice } from '../hooks/useApi';

interface OptionsCardProps {
  preview: string;
  charCount: number;
  detectedLanguage: string;
  languageName: string;
  isPortuguese: boolean;
  onToggleTranslation: () => void;
  translationLoading: boolean;
  translationComplete: boolean;
  voices: Voice[];
  selectedVoice: string;
  onVoiceChange: (voiceId: string) => void;
  speed: number;
  onSpeedChange: (speed: number) => void;
  includeReferences: boolean;
  onIncludeReferencesChange: (value: boolean) => void;
  extractionDiagnostics: Record<string, unknown>;
  extractionWarnings: string[];
  onTranslate: () => void;
  onGenerate: () => void;
  disabled?: boolean;
  canGenerate?: boolean;
}

function readNumber(value: unknown): number | null {
  return typeof value === 'number' ? value : null;
}

function readArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export function OptionsCard({
  preview,
  charCount,
  languageName,
  isPortuguese,
  onToggleTranslation,
  translationLoading,
  translationComplete,
  voices,
  selectedVoice,
  onVoiceChange,
  speed,
  onSpeedChange,
  includeReferences,
  onIncludeReferencesChange,
  extractionDiagnostics,
  extractionWarnings,
  onTranslate,
  onGenerate,
  disabled,
  canGenerate,
}: OptionsCardProps) {
  const femaleVoices = voices.filter((voice) => voice.gender === 'Feminino');
  const maleVoices = voices.filter((voice) => voice.gender === 'Masculino');

  const pages = readNumber(extractionDiagnostics.page_count);
  const pagesExtracted = readNumber(extractionDiagnostics.pages_extracted);
  const skippedPages = readArray(extractionDiagnostics.skipped_pages).length;

  const formatSpeed = (value: number) => {
    if (value === 1) {
      return 'Normal (1.0x)';
    }
    if (value < 1) {
      return `Mais lento (${value.toFixed(2)}x)`;
    }
    return `Mais rapido (${value.toFixed(2)}x)`;
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Passo 2: Configurar</h2>
        <p className="card-subtitle">Revise a extracao, escolha a voz e ajuste a leitura</p>
      </div>

      <div style={{ marginBottom: 'var(--spacing-lg)' }}>
        <h3>Resumo da Extracao</h3>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
            gap: 'var(--spacing-sm)',
            marginBottom: 'var(--spacing-md)',
          }}
        >
          <div className="alert" style={{ margin: 0 }}>
            Paginas: {pages ?? 'n/a'}
          </div>
          <div className="alert" style={{ margin: 0 }}>
            Paginas com texto: {pagesExtracted ?? 'n/a'}
          </div>
          {skippedPages > 0 && (
            <div className="alert" style={{ margin: 0 }}>
              Paginas ignoradas: {skippedPages}
            </div>
          )}
        </div>

        {extractionWarnings.length > 0 && (
          <div className="alert alert-warning" role="alert" style={{ marginBottom: 'var(--spacing-sm)' }}>
            {extractionWarnings.join(' ')}
          </div>
        )}
      </div>

      <div style={{ marginBottom: 'var(--spacing-lg)' }}>
        <h3>Previa do Texto</h3>
        <div className="text-preview" role="region" aria-label="Previa do texto extraido">
          {preview}
        </div>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
          Total: {charCount.toLocaleString('pt-BR')} caracteres
        </p>
      </div>

      <div style={{ marginBottom: 'var(--spacing-lg)' }}>
        <h3>Idioma Detectado</h3>
        <p
          style={{
            fontSize: 'var(--font-size-xl)',
            fontWeight: 600,
            color: isPortuguese ? 'var(--color-success)' : 'var(--color-warning)',
            marginBottom: 'var(--spacing-sm)',
          }}
        >
          {languageName}
        </p>

        {isPortuguese ? (
          <p style={{ color: 'var(--color-success)' }}>
            O texto ja esta em portugues. Nao e necessario traduzir.
          </p>
        ) : (
          <div>
            <p style={{ marginBottom: 'var(--spacing-md)' }}>
              O texto esta em {languageName}. Deseja traduzir para portugues?
            </p>

            {!translationComplete && (
              <div style={{ display: 'flex', gap: 'var(--spacing-md)', flexWrap: 'wrap' }}>
                <button
                  onClick={onTranslate}
                  disabled={translationLoading || disabled}
                  className="btn btn-primary"
                  aria-busy={translationLoading}
                >
                  {translationLoading ? (
                    <>
                      <span className="spinner" />
                      Traduzindo...
                    </>
                  ) : (
                    'Traduzir para Portugues'
                  )}
                </button>
                <button
                  onClick={onToggleTranslation}
                  disabled={translationLoading || disabled}
                  className="btn btn-secondary"
                >
                  Pular traducao
                </button>
              </div>
            )}

            {translationComplete && (
              <div className="alert alert-success" role="status">
                Traducao concluida com sucesso.
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{ marginBottom: 'var(--spacing-lg)' }}>
        <h3>Leitura do Documento</h3>
        <label
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 'var(--spacing-sm)',
            cursor: disabled ? 'not-allowed' : 'pointer',
          }}
        >
          <input
            type="checkbox"
            checked={includeReferences}
            onChange={(event) => onIncludeReferencesChange(event.target.checked)}
            disabled={disabled}
          />
          <span>
            Ler a secao de referencias
            <span
              style={{
                display: 'block',
                color: 'var(--color-text-muted)',
                fontSize: 'var(--font-size-sm)',
                marginTop: 'var(--spacing-xs)',
              }}
            >
              Por padrao o Laris le o titulo, secoes e corpo do artigo, mas nao narra a bibliografia final.
            </span>
          </span>
        </label>
      </div>

      <div style={{ marginBottom: 'var(--spacing-lg)' }}>
        <h3 id="voice-label">Escolha a Voz</h3>
        <div role="radiogroup" aria-labelledby="voice-label">
          {femaleVoices.length > 0 && (
            <div style={{ marginBottom: 'var(--spacing-md)' }}>
              <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-sm)' }}>
                Vozes femininas:
              </p>
              <div style={{ display: 'flex', gap: 'var(--spacing-sm)', flexWrap: 'wrap' }}>
                {femaleVoices.map((voice) => (
                  <button
                    key={voice.id}
                    onClick={() => onVoiceChange(voice.id)}
                    className={`btn ${selectedVoice === voice.id ? 'btn-primary' : 'btn-secondary'}`}
                    role="radio"
                    aria-checked={selectedVoice === voice.id}
                    disabled={disabled}
                  >
                    {voice.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {maleVoices.length > 0 && (
            <div>
              <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-sm)' }}>
                Vozes masculinas:
              </p>
              <div style={{ display: 'flex', gap: 'var(--spacing-sm)', flexWrap: 'wrap' }}>
                {maleVoices.map((voice) => (
                  <button
                    key={voice.id}
                    onClick={() => onVoiceChange(voice.id)}
                    className={`btn ${selectedVoice === voice.id ? 'btn-primary' : 'btn-secondary'}`}
                    role="radio"
                    aria-checked={selectedVoice === voice.id}
                    disabled={disabled}
                  >
                    {voice.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div>
        <h3 id="speed-label">Velocidade da Fala</h3>
        <p
          style={{
            fontSize: 'var(--font-size-xl)',
            fontWeight: 600,
            marginBottom: 'var(--spacing-sm)',
            color: 'var(--color-primary)',
          }}
        >
          {formatSpeed(speed)}
        </p>
        <input
          type="range"
          min="0.5"
          max="1.5"
          step="0.05"
          value={speed}
          onChange={(event) => onSpeedChange(parseFloat(event.target.value))}
          aria-labelledby="speed-label"
          aria-valuemin={0.5}
          aria-valuemax={1.5}
          aria-valuenow={speed}
          aria-valuetext={formatSpeed(speed)}
          disabled={disabled}
          style={{ marginBottom: 'var(--spacing-sm)' }}
        />
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            color: 'var(--color-text-muted)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          <span>Mais lento</span>
          <span>Normal</span>
          <span>Mais rapido</span>
        </div>
      </div>

      <div
        style={{
          marginTop: 'var(--spacing-xl)',
          paddingTop: 'var(--spacing-lg)',
          borderTop: '2px solid var(--color-border)',
        }}
      >
        <button
          onClick={onGenerate}
          disabled={disabled || !canGenerate}
          className="btn btn-primary btn-large"
          style={{ width: '100%' }}
        >
          Gerar Audio Agora
        </button>

        {!canGenerate && !isPortuguese && (
          <p
            style={{
              textAlign: 'center',
              color: 'var(--color-warning)',
              fontSize: 'var(--font-size-sm)',
              marginTop: 'var(--spacing-sm)',
            }}
          >
            Primeiro traduza o texto ou clique em "Pular traducao".
          </p>
        )}

        {canGenerate && (
          <p
            style={{
              textAlign: 'center',
              color: 'var(--color-text-muted)',
              fontSize: 'var(--font-size-sm)',
              marginTop: 'var(--spacing-sm)',
            }}
          >
            Atalho: Alt + G
          </p>
        )}
      </div>
    </div>
  );
}
