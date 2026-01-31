/**
 * Laris - Alert Component
 * Componente de alerta acessível.
 */

import React from 'react';

interface AlertProps {
  type: 'error' | 'success' | 'warning' | 'info';
  message: string;
  onClose?: () => void;
}

export function Alert({ type, message, onClose }: AlertProps) {
  return (
    <div
      className={`alert alert-${type}`}
      role="alert"
      aria-live="assertive"
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>{message}</span>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'inherit',
              fontSize: 'var(--font-size-lg)',
              cursor: 'pointer',
              padding: 'var(--spacing-xs)',
              marginLeft: 'var(--spacing-md)',
            }}
            aria-label="Fechar alerta"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}
