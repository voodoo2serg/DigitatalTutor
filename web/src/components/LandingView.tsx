'use client';

import React from 'react';

interface LandingViewProps {
  onStudentLogin: () => void;
  onAdminLogin: () => void;
}

export default function LandingView({ onStudentLogin, onAdminLogin }: LandingViewProps) {
  return (
    <div className="dt-login-page">
      <div style={{ width: '100%', maxWidth: '720px' }} className="dt-animate-in">
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <h1 style={{
            fontFamily: 'var(--font-heading)',
            fontSize: '2rem',
            color: '#ffffff',
            fontWeight: 700,
            marginBottom: '8px',
          }}>
            DigitalTutor
          </h1>
          <p style={{
            fontSize: '0.9rem',
            color: 'rgba(255,255,255,0.55)',
            lineHeight: 1.6,
            maxWidth: '480px',
            margin: '0 auto',
          }}>
            Система управления учебными проектами и&nbsp;квалификационными работами
          </p>
        </div>

        {/* Two Cards */}
        <div className="dt-grid-2" style={{ gap: '20px' }}>
          {/* Student Card */}
          <button
            onClick={onStudentLogin}
            style={{
              background: 'var(--color-bg-white)',
              borderRadius: 'var(--radius-lg)',
              boxShadow: 'var(--shadow-lg)',
              border: '1px solid var(--color-border)',
              padding: '28px 24px',
              textAlign: 'left',
              cursor: 'pointer',
              transition: 'box-shadow 0.15s ease, transform 0.15s ease',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.boxShadow = '0 8px 32px rgba(0,0,0,0.15)';
              (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.boxShadow = 'var(--shadow-lg)';
              (e.currentTarget as HTMLElement).style.transform = 'translateY(0)';
            }}
          >
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: 'var(--radius-md)',
              background: '#e8f0fe',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.2rem',
            }}>
              &#x1f393;
            </div>
            <h2 style={{
              fontFamily: 'var(--font-heading)',
              fontSize: '1.15rem',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
            }}>
              Вход для студента
            </h2>
            <p style={{
              fontSize: '0.82rem',
              color: 'var(--color-text-secondary)',
              lineHeight: 1.6,
            }}>
              Получите одноразовый код через Telegram-бота и&nbsp;войдите в&nbsp;личный кабинет для отслеживания статуса работ и&nbsp;переписки с&nbsp;преподавателем.
            </p>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.8rem',
              fontWeight: 600,
              color: 'var(--color-accent)',
              marginTop: '4px',
            }}>
              Войти &#x2192;
            </div>
          </button>

          {/* Admin Card */}
          <button
            onClick={onAdminLogin}
            style={{
              background: 'var(--color-bg-white)',
              borderRadius: 'var(--radius-lg)',
              boxShadow: 'var(--shadow-lg)',
              border: '1px solid var(--color-border)',
              padding: '28px 24px',
              textAlign: 'left',
              cursor: 'pointer',
              transition: 'box-shadow 0.15s ease, transform 0.15s ease',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.boxShadow = '0 8px 32px rgba(0,0,0,0.15)';
              (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.boxShadow = 'var(--shadow-lg)';
              (e.currentTarget as HTMLElement).style.transform = 'translateY(0)';
            }}
          >
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: 'var(--radius-md)',
              background: '#f0fdf4',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.2rem',
            }}>
              &#x1f4da;
            </div>
            <h2 style={{
              fontFamily: 'var(--font-heading)',
              fontSize: '1.15rem',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
            }}>
              Вход для преподавателя
            </h2>
            <p style={{
              fontSize: '0.82rem',
              color: 'var(--color-text-secondary)',
              lineHeight: 1.6,
            }}>
              Доступ к&nbsp;панели управления: проверка работ, генерация QR-кодов доступа, анализ материалов и&nbsp;управление студентами.
            </p>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.8rem',
              fontWeight: 600,
              color: 'var(--color-accent)',
              marginTop: '4px',
            }}>
              Войти &#x2192;
            </div>
          </button>
        </div>

        {/* Demo Codes */}
        <div style={{
          textAlign: 'center',
          marginTop: '32px',
          padding: '14px 20px',
          background: 'rgba(255,255,255,0.08)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid rgba(255,255,255,0.1)',
        }}>
          <p style={{
            fontSize: '0.78rem',
            color: 'rgba(255,255,255,0.5)',
            marginBottom: '4px',
          }}>
            Демо-режим
          </p>
          <p style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.8rem',
            color: 'rgba(255,255,255,0.75)',
            letterSpacing: '0.02em',
          }}>
            студент: <strong style={{ color: '#fbbf24' }}>DT-2024-TEST</strong>
            <span style={{ margin: '0 12px', opacity: 0.3 }}>|</span>
            преподаватель: <strong style={{ color: '#fbbf24' }}>ADMIN-2024</strong>
          </p>
        </div>
      </div>
    </div>
  );
}
