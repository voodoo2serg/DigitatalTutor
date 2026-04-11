'use client';

import React, { useState, useEffect, useCallback } from 'react';
import type { User, StudentWork, FileTreeNode } from '@/lib/types';
import { getAllStudents, getAllWorks, getFileTree, generateAccessCode } from '@/lib/api';
import SessionTimer from './SessionTimer';

interface AdminDashboardProps {
  user: User;
  onLogout: () => void;
}

type AdminTab = 'students' | 'works' | 'files' | 'ai' | 'qr-codes' | 'settings';

function formatDate(dateStr?: string): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function formatFileSize(bytes?: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return bytes + ' Б';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' КБ';
  return (bytes / (1024 * 1024)).toFixed(1) + ' МБ';
}

function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    draft: 'Черновик',
    submitted: 'Отправлена',
    in_review: 'На проверке',
    revision_required: 'На доработке',
    accepted: 'Принята',
    rejected: 'Отклонена',
    graded: 'Оценена',
  };
  return map[status] || status;
}

function getScoreColor(score: number | undefined): string {
  if (score === undefined || score === null) return 'var(--color-text-muted)';
  if (score >= 80) return 'var(--color-success)';
  if (score >= 60) return 'var(--color-warning)';
  return 'var(--color-error)';
}

function ScoreCell({ value }: { value: number | undefined }) {
  if (value === undefined || value === null) return <span style={{ color: 'var(--color-text-muted)' }}>—</span>;
  return (
    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.85rem', color: getScoreColor(value) }}>
      {value.toFixed(1)}%
    </span>
  );
}

// ==================== File Tree Node ====================
function FileTreeItem({ node, depth }: { node: FileTreeNode; depth: number }) {
  const [open, setOpen] = useState(false);
  const hasChildren = node.children && node.children.length > 0;

  if (node.type === 'folder') {
    return (
      <div>
        <div
          className="dt-file-node dt-file-node--folder"
          onClick={() => setOpen(!open)}
          style={{ paddingLeft: `${depth * 20 + 8}px` }}
        >
          <span style={{ fontSize: '0.75rem', width: '14px', textAlign: 'center' }}>
            {open ? '▾' : '▸'}
          </span>
          <span>📁 {node.name}</span>
          {hasChildren && (
            <span className="dt-text-xs dt-text-muted" style={{ marginLeft: '4px' }}>
              ({node.children!.length})
            </span>
          )}
        </div>
        {open && hasChildren && (
          <div>
            {node.children!.map((child, i) => (
              <FileTreeItem key={`${child.path}-${i}`} node={child} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className="dt-file-node dt-file-node--file"
      style={{ paddingLeft: `${depth * 20 + 8}px` }}
    >
      <span style={{ width: '14px' }} />
      <span>📄 {node.name}</span>
      <span className="dt-text-xs dt-text-muted" style={{ marginLeft: 'auto' }}>
        {formatFileSize(node.size)}
      </span>
      {node.modified && (
        <span className="dt-text-xs dt-text-muted" style={{ marginLeft: '12px' }}>
          {node.modified}
        </span>
      )}
    </div>
  );
}

export default function AdminDashboard({ user, onLogout }: AdminDashboardProps) {
  const [tab, setTab] = useState<AdminTab>('students');
  const [students, setStudents] = useState<User[]>([]);
  const [works, setWorks] = useState<StudentWork[]>([]);
  const [fileTree, setFileTree] = useState<FileTreeNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedStudent, setExpandedStudent] = useState<string | null>(null);
  const [expandedWork, setExpandedWork] = useState<string | null>(null);

  // QR code state
  const [selectedStudentId, setSelectedStudentId] = useState('');
  const [qrDataUrl, setQrDataUrl] = useState('');
  const [qrCodeText, setQrCodeText] = useState('');
  const [qrExpiresAt, setQrExpiresAt] = useState('');
  const [qrGenerating, setQrGenerating] = useState(false);

  const [sessionStart] = useState(Date.now());

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [s, w, f] = await Promise.all([
        getAllStudents(),
        getAllWorks(),
        getFileTree(),
      ]);
      setStudents(s);
      setWorks(w);
      setFileTree(f);
    } catch {
      // data stays empty
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleGenerateQR = async () => {
    if (!selectedStudentId) return;
    setQrGenerating(true);
    try {
      const result = await generateAccessCode(selectedStudentId);
      setQrCodeText(result.code);

      // Use qrcode library to generate QR
      const QRCode = await import('qrcode');
      const studentName = students.find(s => s.id === selectedStudentId)?.full_name || 'Студент';
      const qrPayload = JSON.stringify({ code: result.code, student_name: studentName, expires_at: result.expires_at });
      const url = await QRCode.toDataURL(qrPayload);
      setQrDataUrl(url);
      setQrExpiresAt(result.expires_at);
    } catch {
      // QR generation failed
    } finally {
      setQrGenerating(false);
    }
  };

  const tabs: { key: AdminTab; label: string }[] = [
    { key: 'students', label: 'Студенты' },
    { key: 'works', label: 'Работы' },
    { key: 'files', label: 'Файлы' },
    { key: 'ai', label: 'Анализ' },
    { key: 'qr-codes', label: 'QR-коды' },
    { key: 'settings', label: 'Настройки' },
  ];

  // Count works per student
  const worksByStudent: Record<string, number> = {};
  works.forEach(w => {
    worksByStudent[w.student_id] = (worksByStudent[w.student_id] || 0) + 1;
  });

  return (
    <div className="dt-content" style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Header */}
      <header className="dt-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span className="dt-header__title">DigitalTutor</span>
          <span className="dt-header__subtitle">Панель управления</span>
        </div>
        <div className="dt-header__actions">
          <SessionTimer startTime={sessionStart} onSessionEnd={onLogout} />
          <span className="dt-text-xs" style={{ color: 'rgba(255,255,255,0.6)' }}>
            {user.full_name}
          </span>
          <button className="dt-btn dt-btn--ghost dt-btn--small" onClick={onLogout} style={{ color: 'rgba(255,255,255,0.7)' }}>
            Выйти
          </button>
        </div>
      </header>

      {/* Tabs */}
      <div className="dt-tabs">
        {tabs.map(t => (
          <button
            key={t.key}
            className={`dt-tab ${tab === t.key ? 'dt-tab--active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Status bar */}
      <div className="dt-status-bar">
        <div className="dt-status-item">
          <div className="dt-status-item__value">{students.length}</div>
          <div className="dt-status-item__label">Студентов</div>
        </div>
        <div className="dt-status-item">
          <div className="dt-status-item__value">{works.length}</div>
          <div className="dt-status-item__label">Работ</div>
        </div>
        <div className="dt-status-item">
          <div className="dt-status-item__value">{works.filter(w => w.status === 'in_review').length}</div>
          <div className="dt-status-item__label">На проверке</div>
        </div>
        <div className="dt-status-item">
          <div className="dt-status-item__value">{works.filter(w => w.status === 'revision_required').length}</div>
          <div className="dt-status-item__label">На доработке</div>
        </div>
      </div>

      {/* Content */}
      <div className="dt-panel" style={{ flex: 1 }}>
        {loading ? (
          <div className="dt-loading">
            <div className="dt-loading__spinner" />
            Загрузка данных...
          </div>
        ) : (
          <>
            {/* Tab: Students */}
            {tab === 'students' && (
              <div className="dt-animate-in">
                <h2 style={{ marginBottom: '16px' }}>Студенты</h2>
                <div className="dt-card">
                  <table className="dt-table">
                    <thead>
                      <tr>
                        <th>ФИО</th>
                        <th>Группа</th>
                        <th>Курс</th>
                        <th>Telegram</th>
                        <th>Статус</th>
                        <th>Работ</th>
                      </tr>
                    </thead>
                    <tbody>
                      {students.map(student => (
                        <React.Fragment key={student.id}>
                          <tr
                            onClick={() => setExpandedStudent(expandedStudent === student.id ? null : student.id)}
                            style={{ cursor: 'pointer' }}
                          >
                            <td style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                              {expandedStudent === student.id ? '▾' : '▸'} {student.full_name}
                            </td>
                            <td>{student.group_name || '—'}</td>
                            <td>{student.course || '—'}</td>
                            <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                              {student.telegram_username ? `@${student.telegram_username}` : '—'}
                            </td>
                            <td>
                              <span className="dt-badge" style={{
                                background: student.is_active ? '#dcfce7' : '#fee2e2',
                                color: student.is_active ? '#166534' : '#991b1b',
                              }}>
                                {student.is_active ? 'Активен' : 'Неактивен'}
                              </span>
                            </td>
                            <td>{worksByStudent[student.id] || 0}</td>
                          </tr>
                          {expandedStudent === student.id && (
                            <tr style={{ background: 'var(--color-bg)' }}>
                              <td colSpan={6} style={{ padding: '16px 20px' }}>
                                <div className="dt-text-sm" style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
                                  <div>
                                    <span className="dt-text-muted">Email:</span> {student.email || '—'}
                                  </div>
                                  <div>
                                    <span className="dt-text-muted">Телефон:</span> {student.phone || '—'}
                                  </div>
                                  <div>
                                    <span className="dt-text-muted">Яндекс.Диск:</span> {student.yandex_folder || '—'}
                                  </div>
                                  <div>
                                    <span className="dt-text-muted">Дата регистрации:</span> {formatDate(student.created_at)}
                                  </div>
                                </div>
                                <div className="dt-text-sm dt-mt-sm">
                                  <span className="dt-text-muted">Всего работ: {worksByStudent[student.id] || 0}</span>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Tab: Works */}
            {tab === 'works' && (
              <div className="dt-animate-in">
                <h2 style={{ marginBottom: '16px' }}>Все работы</h2>
                <div className="dt-card">
                  <div className="dt-scroll" style={{ maxHeight: '600px', overflow: 'auto' }}>
                    <table className="dt-table">
                      <thead>
                        <tr>
                          <th>Студент</th>
                          <th>Название</th>
                          <th>Тип</th>
                          <th>Статус</th>
                          <th>Дедлайн</th>
                          <th>Оценка</th>
                          <th>Антиплагиат</th>
                          <th>Структура</th>
                          <th>Оформление</th>
                        </tr>
                      </thead>
                      <tbody>
                        {works.map(work => (
                          <React.Fragment key={work.id}>
                            <tr
                              onClick={() => setExpandedWork(expandedWork === work.id ? null : work.id)}
                              style={{ cursor: 'pointer' }}
                            >
                              <td style={{ fontWeight: 500 }}>{work.student?.full_name || '—'}</td>
                              <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {expandedWork === work.id ? '▾' : '▸'} {work.title}
                              </td>
                              <td className="dt-text-sm">{work.work_type?.name || '—'}</td>
                              <td>
                                <span className={`dt-badge dt-badge--${work.status}`}>
                                  {getStatusLabel(work.status)}
                                </span>
                              </td>
                              <td className="dt-text-sm">{formatDate(work.deadline)}</td>
                              <td>
                                {work.grade_classic !== undefined
                                  ? `${work.grade_classic} (${work.grade_100 || '—'}%)`
                                  : '—'}
                              </td>
                              <td><ScoreCell value={work.ai_plagiarism_score} /></td>
                              <td><ScoreCell value={work.ai_structure_score} /></td>
                              <td><ScoreCell value={work.ai_formatting_score} /></td>
                            </tr>
                            {expandedWork === work.id && (
                              <tr style={{ background: 'var(--color-bg)' }}>
                                <td colSpan={9} style={{ padding: '16px 20px' }}>
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                    {work.teacher_comment && (
                                      <div>
                                        <div className="dt-text-xs dt-text-muted" style={{ marginBottom: '4px', fontWeight: 600 }}>КОММЕНТАРИЙ ПРЕПОДАВАТЕЛЯ</div>
                                        <div style={{
                                          background: 'var(--color-bg-white)',
                                          padding: '10px 14px',
                                          borderRadius: 'var(--radius-md)',
                                          borderLeft: '3px solid var(--color-accent)',
                                          fontSize: '0.85rem',
                                        }}>
                                          {work.teacher_comment}
                                        </div>
                                      </div>
                                    )}
                                    {work.files && work.files.length > 0 && (
                                      <div>
                                        <div className="dt-text-xs dt-text-muted" style={{ marginBottom: '4px', fontWeight: 600 }}>ФАЙЛЫ</div>
                                        {work.files.map(f => (
                                          <div key={f.id} className="dt-text-sm" style={{ padding: '4px 0' }}>
                                            &#x1f4c4; {f.original_name || f.filename} ({formatFileSize(f.size_bytes)})
                                            <span className="dt-text-muted" style={{ marginLeft: '8px' }}>{formatDate(f.created_at)}</span>
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                    {work.ai_analysis_json && (
                                      <div>
                                        <div className="dt-text-xs dt-text-muted" style={{ marginBottom: '4px', fontWeight: 600 }}>ПОЛНЫЙ АНАЛИЗ</div>
                                        <pre style={{
                                          background: 'var(--color-bg-white)',
                                          padding: '12px',
                                          borderRadius: 'var(--radius-md)',
                                          fontSize: '0.75rem',
                                          fontFamily: 'var(--font-mono)',
                                          overflow: 'auto',
                                          maxHeight: '200px',
                                          border: '1px solid var(--color-border-light)',
                                        }}>
                                          {JSON.stringify(work.ai_analysis_json, null, 2)}
                                        </pre>
                                      </div>
                                    )}
                                    {work.antiplag_originality_percent !== undefined && (
                                      <div className="dt-text-sm">
                                        <span className="dt-text-muted">Антиплагиат ({work.antiplag_system || '—'}):</span>{' '}
                                        <strong style={{ color: getScoreColor(work.antiplag_originality_percent) }}>
                                          {work.antiplag_originality_percent}%
                                        </strong>
                                      </div>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* Tab: Files (Explorer) */}
            {tab === 'files' && (
              <div className="dt-animate-in">
                <h2 style={{ marginBottom: '16px' }}>Проводник файлов</h2>
                {fileTree.length === 0 ? (
                  <div className="dt-empty">
                    <div className="dt-empty__icon">&#x1f4c1;</div>
                    <div className="dt-empty__text">Файловая структура пуста.</div>
                  </div>
                ) : (
                  <div className="dt-card">
                    <div className="dt-card__header">
                      <span style={{ fontWeight: 600 }}>Структура: Группа / Студент / Тип работы / Файлы</span>
                    </div>
                    <div className="dt-card__body">
                      <div className="dt-file-tree">
                        {fileTree.map((node, i) => (
                          <FileTreeItem key={node.path || i} node={node} depth={0} />
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Tab: AI Analysis */}
            {tab === 'ai' && (
              <div className="dt-animate-in">
                <h2 style={{ marginBottom: '16px' }}>Результаты анализа</h2>
                <p className="dt-text-sm dt-text-muted" style={{ marginBottom: '16px' }}>
                  Данные автоматической проверки работ: оригинальность текста, структура документа и оформление по ГОСТ.
                </p>
                <div className="dt-card">
                  <div className="dt-scroll" style={{ maxHeight: '500px', overflow: 'auto' }}>
                    <table className="dt-table">
                      <thead>
                        <tr>
                          <th>Работа</th>
                          <th>Студент</th>
                          <th>Антиплагиат</th>
                          <th>Структура</th>
                          <th>Оформление</th>
                          <th>Проверено</th>
                        </tr>
                      </thead>
                      <tbody>
                        {works.filter(w => w.ai_plagiarism_score !== undefined || w.ai_structure_score !== undefined).map(work => (
                          <tr key={work.id}>
                            <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500 }}>
                              {work.title}
                            </td>
                            <td>{work.student?.full_name || '—'}</td>
                            <td><ScoreCell value={work.ai_plagiarism_score} /></td>
                            <td><ScoreCell value={work.ai_structure_score} /></td>
                            <td><ScoreCell value={work.ai_formatting_score} /></td>
                            <td className="dt-text-sm">{formatDate(work.teacher_reviewed_at || work.updated_at)}</td>
                          </tr>
                        ))}
                        {works.filter(w => w.ai_plagiarism_score !== undefined || w.ai_structure_score !== undefined).length === 0 && (
                          <tr>
                            <td colSpan={6} style={{ textAlign: 'center', padding: '24px', color: 'var(--color-text-muted)' }}>
                              Нет данных анализа
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* Tab: QR Codes */}
            {tab === 'qr-codes' && (
              <div className="dt-animate-in">
                <h2 style={{ marginBottom: '16px' }}>Генерация QR-кодов доступа</h2>
                <div className="dt-card">
                  <div className="dt-card__body">
                    <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', marginBottom: '20px', flexWrap: 'wrap' }}>
                      <div style={{ flex: 1, minWidth: '200px' }}>
                        <label className="dt-input-label">Студент</label>
                        <select
                          className="dt-input"
                          value={selectedStudentId}
                          onChange={(e) => setSelectedStudentId(e.target.value)}
                          style={{ cursor: 'pointer' }}
                        >
                          <option value="">— Выберите студента —</option>
                          {students.map(s => (
                            <option key={s.id} value={s.id}>
                              {s.full_name} ({s.group_name || '—'})
                            </option>
                          ))}
                        </select>
                      </div>
                      <button
                        className="dt-btn dt-btn--primary"
                        onClick={handleGenerateQR}
                        disabled={qrGenerating || !selectedStudentId}
                      >
                        {qrGenerating ? 'Генерация...' : 'Сгенерировать код'}
                      </button>
                    </div>

                    {qrDataUrl && (
                      <div className="dt-qr-container dt-animate-in">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={qrDataUrl} alt="QR-код доступа" width={200} height={200} />
                        <div className="dt-qr-code-text">{qrCodeText}</div>
                        <div className="dt-text-sm dt-text-muted" style={{ marginTop: '8px' }}>
                          Действителен 90 минут
                        </div>
                        <div className="dt-text-xs dt-text-muted" style={{ marginTop: '2px' }}>
                          Истекает: {qrExpiresAt ? new Date(qrExpiresAt).toLocaleString('ru-RU') : '—'}
                        </div>
                      </div>
                    )}

                    {!qrDataUrl && (
                      <div className="dt-empty" style={{ padding: '32px' }}>
                        <div className="dt-empty__icon">&#x1f4f1;</div>
                        <div className="dt-empty__text">
                          Выберите студента и нажмите &laquo;Сгенерировать код&raquo;. Студент сможет отсканировать QR-код для входа в систему.
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Tab: Settings */}
            {tab === 'settings' && (
              <div className="dt-animate-in" style={{ maxWidth: '600px' }}>
                <h2 style={{ marginBottom: '20px' }}>Настройки</h2>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  {/* AI Providers */}
                  <div className="dt-card">
                    <div className="dt-card__header">
                      <span style={{ fontWeight: 600 }}>Провайдер проверки</span>
                    </div>
                    <div className="dt-card__body">
                      <p className="dt-text-sm dt-text-muted" style={{ marginBottom: '12px' }}>
                        Выберите провайдера для автоматической проверки работ. Настройте ключи API.
                      </p>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {['Cerebra', 'OpenRouter', 'Ollama (локально)', 'HuggingFace'].map(provider => (
                          <label key={provider} style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                            padding: '10px 14px',
                            background: 'var(--color-bg)',
                            borderRadius: 'var(--radius-md)',
                            cursor: 'pointer',
                            fontSize: '0.85rem',
                          }}>
                            <input type="radio" name="ai_provider" defaultChecked={provider === 'Cerebra'} />
                            <span style={{ fontWeight: 500 }}>{provider}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Master Code */}
                  <div className="dt-card">
                    <div className="dt-card__header">
                      <span style={{ fontWeight: 600 }}>Мастер-код</span>
                    </div>
                    <div className="dt-card__body">
                      <p className="dt-text-sm dt-text-muted" style={{ marginBottom: '12px' }}>
                        Текущий мастер-код для доступа к панели управления.
                      </p>
                      <div className="dt-flex dt-gap-sm">
                        <input
                          type="text"
                          className="dt-input"
                          value="ADMIN-2024"
                          readOnly
                          style={{ fontFamily: 'var(--font-mono)', maxWidth: '200px' }}
                        />
                        <button className="dt-btn dt-btn--secondary dt-btn--small">
                          Изменить
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* System Status */}
                  <div className="dt-card">
                    <div className="dt-card__header">
                      <span style={{ fontWeight: 600 }}>Состояние системы</span>
                    </div>
                    <div className="dt-card__body">
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <div className="dt-flex dt-flex-between">
                          <span className="dt-text-sm">API сервер</span>
                          <span style={{ color: 'var(--color-success)', fontSize: '0.82rem', fontWeight: 600 }}>
                            &#x2713; Подключён
                          </span>
                        </div>
                        <div className="dt-flex dt-flex-between">
                          <span className="dt-text-sm">Telegram бот</span>
                          <span style={{ color: 'var(--color-success)', fontSize: '0.82rem', fontWeight: 600 }}>
                            &#x2713; Активен
                          </span>
                        </div>
                        <div className="dt-flex dt-flex-between">
                          <span className="dt-text-sm">Яндекс.Диск</span>
                          <span style={{ color: 'var(--color-success)', fontSize: '0.82rem', fontWeight: 600 }}>
                            &#x2713; Подключён
                          </span>
                        </div>
                        <div className="dt-flex dt-flex-between">
                          <span className="dt-text-sm">Версия</span>
                          <span className="dt-text-sm dt-text-muted">1.0.0</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
