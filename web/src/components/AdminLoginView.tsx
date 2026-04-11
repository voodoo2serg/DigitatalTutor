'use client';

import React, { useState } from 'react';

interface AdminLoginViewProps {
  onLogin: (code: string) => void;
  onBack: () => void;
  isLoading: boolean;
  error?: string;
}

export default function AdminLoginView({ onLogin, onBack, isLoading, error }: AdminLoginViewProps) {
  const [code, setCode] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (code.trim()) {
      onLogin(code.trim());
    }
  };

  return (
    <div className="dt-login-page">
      <div className="dt-login-card dt-animate-in" style={{ maxWidth: '400px' }}>
        <div className="dt-login-card__header">
          <h1>Панель преподавателя</h1>
          <p>Введите мастер-код для доступа к управлению</p>
        </div>

        <div className="dt-login-card__body">
          <form onSubmit={handleSubmit}>
            <label className="dt-input-label">Мастер-код</label>
            <input
              type="password"
              className="dt-input dt-input--large"
              placeholder="&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              disabled={isLoading}
              autoFocus
              maxLength={32}
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
