/**
 * Laris - Steps Component
 * Indicador de passos do wizard.
 */

interface StepsProps {
  currentStep: number;
}

const steps = [
  { number: 1, label: 'Enviar arquivo' },
  { number: 2, label: 'Configurar' },
  { number: 3, label: 'Gerar áudio' },
];

export function Steps({ currentStep }: StepsProps) {
  return (
    <nav aria-label="Progresso do processo" style={{ marginBottom: 'var(--spacing-xl)' }}>
      <ol className="steps" style={{ listStyle: 'none' }}>
        {steps.map((step) => {
          const isActive = step.number === currentStep;
          const isCompleted = step.number < currentStep;

          return (
            <li
              key={step.number}
              className={`step ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
              aria-current={isActive ? 'step' : undefined}
            >
              <span className="step-number" aria-hidden="true">
                {isCompleted ? '✓' : step.number}
              </span>
              <span className="step-label">
                {step.label}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
