/**
 * Laris - Upload Card Component
 * Card para upload de arquivos com área de arrastar e soltar.
 */

import React, { useRef, useState } from 'react';

interface UploadCardProps {
  onFileSelect: (file: File) => void;
  loading: boolean;
  disabled?: boolean;
}

export function UploadCard({ onFileSelect, loading, disabled }: UploadCardProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragOver(true);
    }
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    if (disabled) return;

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      validateAndSelect(files[0]);
    }
  };

  const handleClick = () => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
      e.preventDefault();
      fileInputRef.current?.click();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      validateAndSelect(files[0]);
    }
  };

  const validateAndSelect = (file: File) => {
    const validTypes = [
      'application/pdf',
      'text/plain',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ];

    const validExtensions = ['.pdf', '.txt', '.docx'];
    const extension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));

    if (!validTypes.includes(file.type) && !validExtensions.includes(extension)) {
      alert('Tipo de arquivo não suportado. Use PDF, TXT ou DOCX.');
      return;
    }

    if (file.size > 50 * 1024 * 1024) {
      alert('Arquivo muito grande. Máximo: 50 MB.');
      return;
    }

    onFileSelect(file);
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Passo 1: Enviar Arquivo</h2>
        <p className="card-subtitle">
          Envie seu artigo em PDF, DOCX ou TXT (máximo 50 MB)
        </p>
      </div>

      <div
        className={`upload-area ${isDragOver ? 'dragover' : ''}`}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label="Área de upload. Clique ou arraste um arquivo para enviar."
        aria-disabled={disabled}
        style={{ opacity: disabled ? 0.5 : 1 }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.docx"
          onChange={handleFileChange}
          style={{ display: 'none' }}
          aria-hidden="true"
          disabled={disabled}
        />

        {loading ? (
          <>
            <div className="spinner" style={{ marginBottom: 'var(--spacing-md)' }} />
            <p style={{ fontSize: 'var(--font-size-lg)' }}>
              Extraindo texto do arquivo...
            </p>
          </>
        ) : (
          <>
            <div className="upload-icon" aria-hidden="true">
              📄
            </div>
            <p style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600, marginBottom: 'var(--spacing-sm)' }}>
              Clique aqui ou arraste o arquivo
            </p>
            <p style={{ color: 'var(--color-text-secondary)' }}>
              Formatos aceitos: PDF, DOCX, TXT
            </p>
            <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', marginTop: 'var(--spacing-sm)' }}>
              Atalho: Alt + U
            </p>
          </>
        )}
      </div>
    </div>
  );
}
