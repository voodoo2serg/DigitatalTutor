'use client';

import React, { useState } from 'react';

interface StudentLoginViewProps {
  onLogin: (code: string) => void;
  onBack: () => void;
  isLoading: boolean;
  error?: string;
}

export default function StudentLoginView({ onLogin, onBack, isLoading, error }: StudentLoginViewProps) {
  const [code, setCode] = useState('');
  const [showQR, setShowQR] = useState(false);
  const [qrCode, setQrCode] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (code.trim()) {
      onLogin(code.trim());
    }
  };

  const handleQRSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (qrCode.trim()) {
      onLogin(qrCode.trim());
    }
  };

  return (
    <div className="dt-login-page">
      <div className="dt-login-card dt-animate-in">
        <div className="dt-login-card__header">
          <h1>Вход в систему</h1>
          <p>Введите код, полученный в Telegram боте</p>
        </div>

        <div className="dt-login-card__body">
          <form onSubmit={handleSubmit}>
            <label className="dt-input-label">Код доступа</label>
            <input
              type="text"
              className="dt-input dt-input--large"
              placeholder="XXXX-XXXX"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              disabled={isLoading}
              autoFocus
              maxLength={12}
              style={{ marginBottom: '16px' }}
            />

            {error && (
              <p style={{
                color: 'var(--color-error)',
                fontSize: '0.82rem',
                marginBottom: '12px',
                textAlign: 'center',
              }}>
                {error}
              </p>
            )}

            <button
              type="submit"
              className="dt-btn dt-btn--primary dt-btn--large"
              disabled={isLoading || !code.trim()}
              style={{ width: '100%' }}
            >
              {isLoading ? 'Вход...' : 'Войти'}
            </button>
          </form>

          <hr className="dt-divider" />

          <div style={{ textAlign: 'center' }}>
            <button
              className="dt-btn dt-btn--ghost"
              onClick={() => setShowQR(!showQR)}
              type="button"
            >
              {showQR ? 'Скрыть ввод QR-кода' : 'У меня нет Telegram / Ввести код с QR'}
            </button>
          </div>

          {showQR && (
            <div className="dt-animate-in" style={{ marginTop: '16px' }}>
              <div style={{
                padding: '16px',
                background: 'var(--color-bg)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border-light)',
              }}>
                <p className="dt-text-sm dt-text-muted" style={{ marginBottom: '8px' }}>
                  Наведите камеру на QR-код, выданный преподавателем, или введите код вручную.
                </p>

                <form onSubmit={handleQRSubmit}>
                  <label className="dt-input-label">Код с QR-кода</label>
                  <input
                    type="text"
                    className="dt-input"
                    placeholder="Введите код..."
                    value={qrCode}
                    onChange={(e) => setQrCode(e.target.value.toUpperCase())}
                    disabled={isLoading}
                    maxLength={12}
                    style={{ marginBottom: '12px' }}
                  />
                  <button
                    type="submit"
                    className="dt-btn dt-btn--primary"
                    disabled={isLoading || !qrCode.trim()}
                    style={{ width: '100%' }}
                  >
                    Войти по QR-коду
                  </button>
                </form>

                <div style={{
                  marginTop: '12px',
                  padding: '20px',
                  background: 'var(--color-bg-white)',
                  border: '1px dashed var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                  textAlign: 'center',
                }}>
                  <p className="dt-text-muted dt-text-sm">
                    [ Область сканирования камеры ]
                  </p>
                  <p className="dt-text-xs dt-text-muted" style={{ marginTop: '4px' }}>
                    Дайте разрешение на использование камеры для автоматического распознавания QR-кода
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="dt-login-card__footer">
          <button
            className="dt-btn dt-btn--ghost dt-btn--small"
            onClick={onBack}
            type="button"
          >
            &#x2190; Назад
          </button>
        </div>
      </div>
    </div>
  );
}
