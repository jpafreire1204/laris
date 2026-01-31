/**
 * Laris - Header Component
 * Cabeçalho com controles de acessibilidade.
 */

import React from 'react';

interface HeaderProps {
  fontSize: number;
  onFontSizeChange: (size: number) => void;
  contrast: 'normal' | 'super';
  onContrastChange: (contrast: 'normal' | 'super') => void;
}

export function Header({
  fontSize,
  onFontSizeChange,
  contrast,
  onContrastChange,
}: HeaderProps) {
  const handleIncrease = () => {
    if (fontSize < 28) {
      onFontSizeChange(fontSize + 2);
    }
  };

  const handleDecrease = () => {
    if (fontSize > 14) {
      onFontSizeChange(fontSize - 2);
    }
  };

  const toggleContrast = () => {
    onContrastChange(contrast === 'normal' ? 'super' : 'normal');
  };

  return (
    <header style={{ marginBottom: 'var(--spacing-lg)' }}>
      {/* Skip link para acessibilidade */}
      <a href="#main-content" className="skip-link">
        Pular para o conteúdo principal
      </a>

      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 'var(--spacing-md)',
      }}>
        <div>
          <h1 style={{ marginBottom: 'var(--spacing-xs)' }}>
            Laris
          </h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-lg)' }}>
            Artigos em Áudio
          </p>
        </div>

        <div className="accessibility-controls" role="group" aria-label="Controles de acessibilidade">
          <button
            onClick={handleDecrease}
            className="btn btn-secondary"
            aria-label="Diminuir tamanho da fonte"
            title="Diminuir fonte (Ctrl+-)"
          >
            A-
          </button>
          <button
            onClick={handleIncrease}
            className="btn btn-secondary"
            aria-label="Aumentar tamanho da fonte"
            title="Aumentar fonte (Ctrl++)"
          >
            A+
          </button>
          <button
            onClick={toggleContrast}
            className="btn btn-secondary"
            aria-label={contrast === 'normal' ? 'Ativar super contraste' : 'Desativar super contraste'}
            title="Alternar contraste"
          >
            {contrast === 'normal' ? 'Super Contraste' : 'Contraste Normal'}
          </button>
        </div>
      </div>

      <hr style={{
        border: 'none',
        borderTop: '2px solid var(--color-border)',
        margin: 'var(--spacing-lg) 0',
      }} />
    </header>
  );
}
