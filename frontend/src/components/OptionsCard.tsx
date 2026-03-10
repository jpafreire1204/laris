/**
 * Laris - Options Card Component
 * Card para configuracao de voz e geracao de audio.
 */

import { Voice } from '../hooks/useApi';

interface OptionsCardProps {
  preview: string;
  charCount: number;
  voices: Voice[];
  selectedVoice: string;
  onVoiceChange: (voiceId: string) => void;
  speed: number;
  onSpeedChange: (speed: number) => void;
  onGenerate: () => void;
  disabled?: boolean;
}

export function OptionsCard({
  preview,
  charCount,
  voices,
  selectedVoice,
  onVoiceChange,
  speed,
  onSpeedChange,
  onGenerate,
  disabled,
}: OptionsCardProps) {
  const formatSpeed = (value: number) => {
    if (value === 1) return 'Normal (1.0x)';
    if (value < 1) return `Mais lento (${value.toFixed(2)}x)`;
    return `Mais rapido (${value.toFixed(2)}x)`;
  };

  const femaleVoices = voices.filter(v => v.gender === 'Feminino');
  const maleVoices = voices.filter(v => v.gender === 'Masculino');

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Passo 2: Configurar</h2>
      </div>

      {/* Previa do texto */}
      <div style={{ marginBottom: 'var(--spacing-lg)' }}>
        <h3>Previa do Texto</h3>
        <div
          className="text-preview"
          role="region"
          aria-label="Previa do texto extraido"
        >
          {preview}
        </div>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
          Total: {charCount.toLocaleString('pt-BR')} caracteres
        </p>
      </div>

      {/* Selecao de voz */}
      <div style={{ marginBottom: 'var(--spacing-lg)' }}>
        <h3 id="voice-label">Escolha a Voz</h3>

        <div role="radiogroup" aria-labelledby="voice-label">
          {femaleVoices.length > 0 && (
            <div style={{ marginBottom: 'var(--spacing-md)' }}>
              <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--spacing-sm)' }}>
                Vozes Femininas:
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
                Vozes Masculinas:
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

      {/* Controle de velocidade */}
      <div>
        <h3 id="speed-label">Velocidade da Fala</h3>
        <p style={{
          fontSize: 'var(--font-size-xl)',
          fontWeight: 600,
          marginBottom: 'var(--spacing-sm)',
          color: 'var(--color-primary)',
        }}>
          {formatSpeed(speed)}
        </p>
        <input
          type="range"
          min="0.5"
          max="1.5"
          step="0.05"
          value={speed}
          onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
          aria-labelledby="speed-label"
          aria-valuemin={0.5}
          aria-valuemax={1.5}
          aria-valuenow={speed}
          aria-valuetext={formatSpeed(speed)}
          disabled={disabled}
          style={{ marginBottom: 'var(--spacing-sm)' }}
        />
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          color: 'var(--color-text-muted)',
          fontSize: 'var(--font-size-sm)',
        }}>
          <span>Mais lento</span>
          <span>Normal</span>
          <span>Mais rapido</span>
        </div>
      </div>

      {/* Botao Gerar Audio */}
      <div style={{ marginTop: 'var(--spacing-xl)', paddingTop: 'var(--spacing-lg)', borderTop: '2px solid var(--color-border)' }}>
        <button
          onClick={onGenerate}
          disabled={disabled}
          className="btn btn-primary btn-large"
          style={{ width: '100%' }}
        >
          Gerar Audio
        </button>
        <p style={{
          textAlign: 'center',
          color: 'var(--color-text-muted)',
          fontSize: 'var(--font-size-sm)',
          marginTop: 'var(--spacing-sm)',
        }}>
          Atalho: Alt + G
        </p>
      </div>
    </div>
  );
}
