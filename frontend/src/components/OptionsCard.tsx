/**
 * Laris - Options Card Component
 * Card para configuração de tradução e voz.
 */

import React from 'react';
import { Voice } from '../hooks/useApi';

interface OptionsCardProps {
  // Dados extraídos
  preview: string;
  charCount: number;
  detectedLanguage: string;
  languageName: string;
  isPortuguese: boolean;

  // Tradução
  needsTranslation: boolean;
  onToggleTranslation: () => void;
  translationLoading: boolean;
  translationComplete: boolean;

  // Voz
  voices: Voice[];
  selectedVoice: string;
  onVoiceChange: (voiceId: string) => void;

  // Velocidade
  speed: number;
  onSpeedChange: (speed: number) => void;

  // Ações
  onTranslate: () => void;
  onGenerate: () => void;
  disabled?: boolean;
  canGenerate?: boolean;
}

export function OptionsCard({
  preview,
  charCount,
  detectedLanguage,
  languageName,
  isPortuguese,
  needsTranslation,
  onToggleTranslation,
  translationLoading,
  translationComplete,
  voices,
  selectedVoice,
  onVoiceChange,
  speed,
  onSpeedChange,
  onTranslate,
  onGenerate,
  disabled,
  canGenerate,
}: OptionsCardProps) {
  const formatSpeed = (value: number) => {
    if (value === 1) return 'Normal (1.0x)';
    if (value < 1) return `Mais lento (${value.toFixed(2)}x)`;
    return `Mais rápido (${value.toFixed(2)}x)`;
  };

  const femaleVoices = voices.filter(v => v.gender === 'Feminino');
  const maleVoices = voices.filter(v => v.gender === 'Masculino');

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Passo 2: Configurar</h2>
        <p className="card-subtitle">
          Ajuste a tradução e escolha a voz
        </p>
      </div>

      {/* Prévia do texto */}
      <div style={{ marginBottom: 'var(--spacing-lg)' }}>
        <h3>Prévia do Texto</h3>
        <div
          className="text-preview"
          role="region"
          aria-label="Prévia do texto extraído"
        >
          {preview}
        </div>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
          Total: {charCount.toLocaleString('pt-BR')} caracteres
        </p>
      </div>

      {/* Idioma detectado */}
      <div style={{ marginBottom: 'var(--spacing-lg)' }}>
        <h3>Idioma Detectado</h3>
        <p style={{
          fontSize: 'var(--font-size-xl)',
          fontWeight: 600,
          color: isPortuguese ? 'var(--color-success)' : 'var(--color-warning)',
          marginBottom: 'var(--spacing-sm)',
        }}>
          {languageName}
        </p>

        {isPortuguese ? (
          <p style={{ color: 'var(--color-success)' }}>
            O texto já está em português. Não é necessário traduzir.
          </p>
        ) : (
          <div>
            <p style={{ marginBottom: 'var(--spacing-md)' }}>
              O texto está em {languageName}. Deseja traduzir para português?
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
                    'Traduzir para Português'
                  )}
                </button>
                <button
                  onClick={onToggleTranslation}
                  disabled={translationLoading || disabled}
                  className="btn btn-secondary"
                >
                  Pular tradução
                </button>
              </div>
            )}

            {translationComplete && (
              <div className="alert alert-success" role="status">
                Tradução concluída com sucesso!
              </div>
            )}
          </div>
        )}
      </div>

      {/* Seleção de voz */}
      <div style={{ marginBottom: 'var(--spacing-lg)' }}>
        <h3 id="voice-label">Escolha a Voz</h3>

        <div role="radiogroup" aria-labelledby="voice-label">
          {/* Vozes femininas */}
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

          {/* Vozes masculinas */}
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
          <span>Mais rápido</span>
        </div>
      </div>

      {/* Botão Gerar Áudio - sempre visível no Passo 2 */}
      <div style={{ marginTop: 'var(--spacing-xl)', paddingTop: 'var(--spacing-lg)', borderTop: '2px solid var(--color-border)' }}>
        <button
          onClick={onGenerate}
          disabled={disabled || !canGenerate}
          className="btn btn-primary btn-large"
          style={{ width: '100%' }}
        >
          🔊 Gerar Áudio Agora
        </button>
        {!canGenerate && !isPortuguese && (
          <p style={{
            textAlign: 'center',
            color: 'var(--color-warning)',
            fontSize: 'var(--font-size-sm)',
            marginTop: 'var(--spacing-sm)',
          }}>
            Primeiro traduza o texto ou clique em "Pular tradução"
          </p>
        )}
        {canGenerate && (
          <p style={{
            textAlign: 'center',
            color: 'var(--color-text-muted)',
            fontSize: 'var(--font-size-sm)',
            marginTop: 'var(--spacing-sm)',
          }}>
            Atalho: Alt + G
          </p>
        )}
      </div>
    </div>
  );
}
