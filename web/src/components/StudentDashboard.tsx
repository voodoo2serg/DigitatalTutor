'use client';

import React, { useState, useEffect } from 'react';
import type { User, StudentWork, Communication, FileRecord } from '@/lib/types';
import { getStudentWorks, getStudentCommunications, getStudentFiles } from '@/lib/api';
import SessionTimer from './SessionTimer';

interface StudentDashboardProps {
  user: User;
  onLogout: () => void;
}

type StudentTab = 'works' | 'archive' | 'files' | 'help';

function formatFileSize(bytes?: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return bytes + ' Б';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' КБ';
  return (bytes / (1024 * 1024)).toFixed(1) + ' МБ';
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function formatDateTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }) +
    ' ' + d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
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

function getDeadlineClass(deadline?: string): string {
  if (!deadline) return '';
  const now = Date.now();
  const dl = new Date(deadline).getTime();
  const diff = dl - now;
  if (diff < 0) return 'dt-deadline--overdue';
  if (diff < 3 * 24 * 60 * 60 * 1000) return 'dt-deadline--soon';
  return 'dt-deadline--ok';
}

export default function StudentDashboard({ user, onLogout }: StudentDashboardProps) {
  const [tab, setTab] = useState<StudentTab>('works');
  const [works, setWorks] = useState<StudentWork[]>([]);
  const [communications, setCommunications] = useState<Communication[]>([]);
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [sessionStart] = useState(Date.now());

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [w, c, f] = await Promise.all([
          getStudentWorks(user.id),
          getStudentCommunications(user.id),
          getStudentFiles(user.id),
        ]);
        setWorks(w);
        setCommunications(c);
        setFiles(f);
      } catch {
        // data stays empty
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [user.id]);

  const activeWorks = works.filter(w => !w.is_archived);
  const archivedWorks = works.filter(w => w.is_archived);

  const workTitleMap: Record<string, string> = {};
  works.forEach(w => {
    workTitleMap[w.id] = w.title;
  });

  const tabs: { key: StudentTab; label: string }[] = [
    { key: 'works', label: 'Мои работы' },
    { key: 'archive', label: 'Переписка' },
    { key: 'files', label: 'Файлы' },
    { key: 'help', label: 'Помощь' },
  ];

  // Group communications by work
  const groupedComms: { workId: string; workTitle: string; messages: Communication[] }[] = [];
  const commMap: Record<string, Communication[]> = {};
  communications.forEach(comm => {
    const wid = comm.work_id || 'general';
    if (!commMap[wid]) commMap[wid] = [];
    commMap[wid].push(comm);
  });
  for (const [wid, msgs] of Object.entries(commMap)) {
    groupedComms.push({
      workId: wid,
      workTitle: workTitleMap[wid] || 'Общая переписка',
      messages: msgs.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()),
    });
  }

  return (
    <div className="dt-content" style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Header */}
      <header className="dt-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span className="dt-header__title">DigitalTutor</span>
          <span className="dt-header__subtitle">Личный кабинет студента</span>
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

      {/* Content */}
      <div className="dt-panel">
        {loading ? (
          <div className="dt-loading">
            <div className="dt-loading__spinner" />
            Загрузка данных...
          </div>
        ) : (
          <>
            {/* Tab: Works */}
            {tab === 'works' && (
              <div className="dt-animate-in">
                <h2 style={{ marginBottom: '16px' }}>Мои работы</h2>
                {activeWorks.length === 0 ? (
                  <div className="dt-empty">
                    <div className="dt-empty__icon">&#x1f4c4;</div>
                    <div className="dt-empty__text">У вас пока нет активных работ. Загрузите материал через Telegram-бота.</div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {activeWorks.map(work => (
                      <div key={work.id} className="dt-work-card">
                        <div className="dt-work-card__title">{work.title}</div>
                        <div className="dt-work-card__meta">
                          {work.work_type && (
                            <span>{work.work_type.name}</span>
                          )}
                          <span className={`dt-badge dt-badge--${work.status}`}>
                            {getStatusLabel(work.status)}
                          </span>
                        </div>
                        {work.deadline && (
                          <div className={`dt-deadline ${getDeadlineClass(work.deadline)}`} style={{ marginBottom: work.teacher_comment ? '0' : '0' }}>
                            &#x1f4c5; Дедлайн: {formatDate(work.deadline)}
                          </div>
                        )}
                        {work.teacher_comment && (
                          <div className="dt-work-card__comment">
                            <div className="dt-work-card__comment-label">Комментарий преподавателя</div>
                            {work.teacher_comment}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {archivedWorks.length > 0 && (
                  <>
                    <h3 style={{ marginTop: '24px', marginBottom: '12px', color: 'var(--color-text-muted)' }}>
                      Архивные работы
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {archivedWorks.map(work => (
                        <div key={work.id} className="dt-work-card" style={{ opacity: 0.7 }}>
                          <div className="dt-work-card__title">{work.title}</div>
                          <div className="dt-work-card__meta">
                            {work.work_type && <span>{work.work_type.name}</span>}
                            <span className={`dt-badge dt-badge--${work.status}`}>
                              {getStatusLabel(work.status)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Tab: Communications */}
            {tab === 'archive' && (
              <div className="dt-animate-in">
                <h2 style={{ marginBottom: '16px' }}>Переписка</h2>
                {groupedComms.length === 0 ? (
                  <div className="dt-empty">
                    <div className="dt-empty__icon">&#x1f4ac;</div>
                    <div className="dt-empty__text">Переписка пока отсутствует. Напишите преподавателю через Telegram-бота.</div>
                  </div>
                ) : (
                  groupedComms.map(group => (
                    <div key={group.workId} style={{ marginBottom: '24px' }}>
                      <div style={{
                        fontSize: '0.85rem',
                        fontWeight: 700,
                        color: 'var(--color-text-primary)',
                        marginBottom: '12px',
                        paddingBottom: '8px',
                        borderBottom: '1px solid var(--color-border)',
                        fontFamily: 'var(--font-heading)',
                      }}>
                        {group.workTitle}
                      </div>
                      <div className="dt-thread">
                        {group.messages.map(msg => {
                          let msgClass = 'dt-message ';
                          if (msg.from_student) msgClass += 'dt-message--student';
                          else if (msg.from_teacher) msgClass += 'dt-message--teacher';
                          else msgClass += 'dt-message--system';

                          const senderName = msg.from_student
                            ? (msg.from_user?.full_name || 'Вы')
                            : (msg.from_user?.full_name || 'Преподаватель');

                          return (
                            <div key={msg.id} className={msgClass}>
                              {msg.message_type !== 'system' && (
                                <div className="dt-message__sender">{senderName}</div>
                              )}
                              <div className="dt-message__text">{msg.content || ''}</div>
                              <div className="dt-message__time">{formatDateTime(msg.created_at)}</div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Tab: Files */}
            {tab === 'files' && (
              <div className="dt-animate-in">
                <h2 style={{ marginBottom: '16px' }}>Мои файлы</h2>
                {files.length === 0 ? (
                  <div className="dt-empty">
                    <div className="dt-empty__icon">&#x1f4c1;</div>
                    <div className="dt-empty__text">Файлы пока не загружены. Отправьте файл через Telegram-бота.</div>
                  </div>
                ) : (
                  <div className="dt-card">
                    <table className="dt-table">
                      <thead>
                        <tr>
                          <th>Файл</th>
                          <th>Размер</th>
                          <th>Дата загрузки</th>
                          <th>Работа</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {files.map(file => (
                          <tr key={file.id}>
                            <td style={{ fontWeight: 500, color: 'var(--color-text-primary)' }}>
                              &#x1f4c4; {file.original_name || file.filename}
                            </td>
                            <td>{formatFileSize(file.size_bytes)}</td>
                            <td>{formatDate(file.created_at)}</td>
                            <td className="dt-text-sm">{workTitleMap[file.work_id] || '—'}</td>
                            <td>
                              <button className="dt-btn dt-btn--secondary dt-btn--small">
                                Скачать
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Tab: Help */}
            {tab === 'help' && (
              <div className="dt-animate-in" style={{ maxWidth: '680px' }}>
                <h2 style={{ marginBottom: '20px' }}>Справка</h2>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  <section>
                    <h3>Как работает система</h3>
                    <p style={{ marginTop: '6px' }}>
                      DigitalTutor — это система для управления учебными проектами. Вы загружаете свои работы через Telegram-бота,
                      преподаватель проверяет их и оставляет комментарии. Статус работы обновляется автоматически, вы можете
                      отслеживать прогресс в разделе &laquo;Мои работы&raquo;.
                    </p>
                  </section>

                  <hr className="dt-divider" />

                  <section>
                    <h3>Как сдать работу</h3>
                    <p style={{ marginTop: '6px' }}>
                      Отправьте файл с работой в Telegram-бот. Бот автоматически зарегистрирует работу и назначит ей статус
                      &laquo;Отправлена&raquo;. После этого преподаватель начнёт проверку. Вы получите уведомление, когда статус изменится.
                      Для повторной отправки обновлённой версии просто отправьте новый файл по тому же заданию.
                    </p>
                  </section>

                  <hr className="dt-divider" />

                  <section>
                    <h3>Статусы работ</h3>
                    <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                        <span className="dt-badge dt-badge--draft">Черновик</span>
                        <span style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                          Работа создана, но ещё не отправлена на проверку.
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                        <span className="dt-badge dt-badge--submitted">Отправлена</span>
                        <span style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                          Файл загружен и ожидает начала проверки преподавателем.
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                        <span className="dt-badge dt-badge--in_review">На проверке</span>
                        <span style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                          Преподаватель просматривает работу. Дождитесь результата.
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                        <span className="dt-badge dt-badge--revision_required">На доработке</span>
                        <span style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                          Преподаватель внёс замечания. Ознакомьтесь с комментариями, внесите исправления и отправьте обновлённую версию.
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                        <span className="dt-badge dt-badge--accepted">Принята</span>
                        <span style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                          Работа успешно прошла проверку и принята без доработок.
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                        <span className="dt-badge dt-badge--graded">Оценена</span>
                        <span style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                          Работа проверена и получила итоговую оценку.
                        </span>
                      </div>
                    </div>
                  </section>

                  <hr className="dt-divider" />

                  <section>
                    <h3>Переписка с преподавателем</h3>
                    <p style={{ marginTop: '6px' }}>
                      Вся переписка привязана к конкретной работе. Чтобы задать вопрос по работе, напишите в Telegram-бот,
                      выбрав нужную работу. Сообщения отображаются в разделе &laquo;Переписка&raquo;. Системные уведомления (например,
                      о смене статуса) также появляются там.
                    </p>
                  </section>

                  <hr className="dt-divider" />

                  <section>
                    <h3>Допустимые форматы файлов</h3>
                    <p style={{ marginTop: '6px' }}>
                      Система принимает документы в форматах: <strong>DOCX</strong>, <strong>PDF</strong>, <strong>ODT</strong>.
                      Рекомендуемый формат — <strong>DOCX</strong> для редактирования или <strong>PDF</strong> для финальной версии.
                      Обратите внимание на требования к оформлению (ГОСТ), указанные в описании типа работы.
                    </p>
                  </section>

                  <hr className="dt-divider" />

                  <section>
                    <h3>Контактная информация</h3>
                    <p style={{ marginTop: '6px' }}>
                      По техническим вопросам обращайтесь через Telegram-бот или к вашему преподавателю.
                      Время ответа: обычно в течение рабочего дня.
                    </p>
                  </section>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
