/**
 * Laris - Header Component
 * Cabeçalho moderno com controles de acessibilidade.
 */

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
    <header style={{ marginBottom: 'var(--spacing-xl)' }}>
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
        padding: 'var(--spacing-md) 0',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)' }}>
          {/* Logo/Icon */}
          <div style={{
            width: '48px',
            height: '48px',
            background: contrast === 'super'
              ? '#ffff00'
              : 'linear-gradient(135deg, var(--color-primary), var(--color-primary-hover))',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '24px',
            boxShadow: 'var(--shadow-md)',
            border: contrast === 'super' ? '2px solid #ffff00' : 'none',
          }}>
            🔊
          </div>
          <div>
            <h1 style={{
              marginBottom: 0,
              fontSize: 'var(--font-size-xl)',
              fontWeight: 700,
              background: 'linear-gradient(135deg, var(--color-text), var(--color-text-secondary))',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: contrast === 'super' ? 'var(--color-text)' : 'transparent',
              backgroundClip: 'text',
            }}>
              Laris
            </h1>
            <p style={{
              color: 'var(--color-text-muted)',
              fontSize: 'var(--font-size-sm)',
              margin: 0,
            }}>
              Texto em Audio
            </p>
          </div>
        </div>

        <div
          className="accessibility-controls"
          role="group"
          aria-label="Controles de acessibilidade"
          style={{
            display: 'flex',
            gap: 'var(--spacing-xs)',
            background: contrast === 'super' ? '#111111' : 'var(--color-bg-hover)',
            padding: 'var(--spacing-xs)',
            borderRadius: 'var(--radius-md)',
            border: contrast === 'super' ? '1px solid #444444' : 'none',
          }}
        >
          <button
            onClick={handleDecrease}
            style={{
              padding: 'var(--spacing-sm) var(--spacing-md)',
              background: 'transparent',
              border: contrast === 'super' ? '1px solid #555' : 'none',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              color: 'var(--color-text)',
              fontWeight: 600,
              fontSize: 'var(--font-size-sm)',
              transition: 'background var(--transition)',
            }}
            aria-label="Diminuir tamanho da fonte"
            title="Diminuir fonte"
            onMouseOver={(e) => e.currentTarget.style.background = contrast === 'super' ? '#1a1a1a' : 'var(--color-bg)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
          >
            A-
          </button>
          <button
            onClick={handleIncrease}
            style={{
              padding: 'var(--spacing-sm) var(--spacing-md)',
              background: 'transparent',
              border: contrast === 'super' ? '1px solid #555' : 'none',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              color: 'var(--color-text)',
              fontWeight: 600,
              fontSize: 'var(--font-size-sm)',
              transition: 'background var(--transition)',
            }}
            aria-label="Aumentar tamanho da fonte"
            title="Aumentar fonte"
            onMouseOver={(e) => e.currentTarget.style.background = contrast === 'super' ? '#1a1a1a' : 'var(--color-bg)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
          >
            A+
          </button>
          <button
            onClick={toggleContrast}
            style={{
              padding: 'var(--spacing-sm) var(--spacing-md)',
              background: contrast === 'super' ? '#ffff00' : 'transparent',
              border: contrast === 'super' ? '2px solid #ffff00' : 'none',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              color: contrast === 'super' ? '#000000' : 'var(--color-text)',
              fontWeight: 700,
              fontSize: 'var(--font-size-sm)',
              transition: 'all var(--transition)',
            }}
            aria-label={contrast === 'normal' ? 'Ativar super contraste' : 'Desativar super contraste'}
            title="Alternar contraste"
          >
            {contrast === 'normal' ? 'Alto Contraste' : 'Contraste ON'}
          </button>
        </div>
      </div>
    </header>
  );
}
