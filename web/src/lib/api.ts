/**
 * DigitalTutor Web Interface — API Client
 * Connects to FastAPI backend for data operations
 */

import type {
  User,
  StudentWork,
  Communication,
  FileRecord,
  LoginResponse,
  FileTreeNode,
} from './types';

// Backend URL — configurable via environment
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

// ==================== Generic Fetch ====================
async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const token = typeof window !== 'undefined'
    ? localStorage.getItem('dt_token')
    : null;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BACKEND_URL}/api/v1${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

// ==================== Auth ====================
export async function validateStudentCode(code: string): Promise<LoginResponse> {
  try {
    const data = await apiFetch<{ valid: boolean; user?: User; token?: string }>(
      `/auth/web-login`,
      {
        method: 'POST',
        body: JSON.stringify({ code }),
      }
    );

    if (data.valid && data.user && data.token) {
      return {
        success: true,
        token: data.token,
        user: data.user,
      };
    }
    return { success: false, error: 'Неверный код или код истёк' };
  } catch {
    // Fallback: demo mode with mock data
    return validateDemoCode(code);
  }
}

export async function validateAdminCode(masterCode: string): Promise<LoginResponse> {
  try {
    const data = await apiFetch<{ valid: boolean; token?: string }>(
      `/auth/admin-login`,
      {
        method: 'POST',
        body: JSON.stringify({ master_code: masterCode }),
      }
    );

    if (data.valid && data.token) {
      return { success: true, token: data.token };
    }
    return { success: false, error: 'Неверный мастер-код' };
  } catch {
    return validateDemoAdminCode(masterCode);
  }
}

// ==================== Demo Mode ====================
const DEMO_STUDENT_CODE = 'DT-2024-TEST';
const DEMO_ADMIN_CODE = 'ADMIN-2024';

function validateDemoCode(code: string): LoginResponse {
  if (code.toUpperCase() === DEMO_STUDENT_CODE) {
    const user: User = getMockStudent();
    return {
      success: true,
      token: 'demo-student-token-' + Date.now(),
      user,
    };
  }
  return { success: false, error: 'Неверный код. Введите код, полученный в Telegram боте.' };
}

function validateDemoAdminCode(code: string): LoginResponse {
  if (code.toUpperCase() === DEMO_ADMIN_CODE) {
    return {
      success: true,
      token: 'demo-admin-token-' + Date.now(),
      user: getMockAdmin(),
    };
  }
  return { success: false, error: 'Неверный мастер-код' };
}

// ==================== Student API ====================
export async function getStudentProfile(): Promise<User> {
  try {
    return await apiFetch<User>('/users/me');
  } catch {
    return getMockStudent();
  }
}

export async function getStudentWorks(studentId: string): Promise<StudentWork[]> {
  try {
    return await apiFetch<StudentWork[]>(`/works?student_id=${studentId}`);
  } catch {
    return getMockStudentWorks(studentId);
  }
}

export async function getStudentCommunications(studentId: string): Promise<Communication[]> {
  try {
    return await apiFetch<Communication[]>(`/communications/student/${studentId}`);
  } catch {
    return getMockCommunications();
  }
}

export async function getStudentFiles(studentId: string): Promise<FileRecord[]> {
  try {
    return await apiFetch<FileRecord[]>(`/files/student/${studentId}`);
  } catch {
    return getMockFiles();
  }
}

// ==================== Admin API ====================
export async function getAllStudents(): Promise<User[]> {
  try {
    return await apiFetch<User[]>('/users?role=student');
  } catch {
    return getMockStudents();
  }
}

export async function getAllWorks(): Promise<StudentWork[]> {
  try {
    return await apiFetch<StudentWork[]>('/works');
  } catch {
    return getMockAllWorks();
  }
}

export async function getFileTree(): Promise<FileTreeNode[]> {
  try {
    return await apiFetch<FileTreeNode[]>('/files/tree');
  } catch {
    return getMockFileTree();
  }
}

export async function generateAccessCode(studentId: string): Promise<{ code: string; qr_data: string; expires_at: string }> {
  try {
    return await apiFetch('/admin/generate-code', {
      method: 'POST',
      body: JSON.stringify({ student_id: studentId }),
    });
  } catch {
    const code = `DT-${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
    const expires = new Date(Date.now() + 90 * 60 * 1000).toISOString();
    return {
      code,
      qr_data: JSON.stringify({ code, expires_at: expires }),
      expires_at: expires,
    };
  }
}

// ==================== Mock Data ====================
function getMockStudent(): User {
  return {
    id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    telegram_id: 123456789,
    telegram_username: 'student_ivanov',
    full_name: 'Иванов Иван Иванович',
    email: 'ivanov@university.ru',
    phone: '+7 999 123-45-67',
    role: 'Студент',
    group_name: 'ИС-101',
    course: 3,
    is_active: true,
    yandex_folder: '/DigitalTutor/ВКР_Бакалавр/ИС-101_Иванов',
    created_at: '2024-09-01T10:00:00Z',
  };
}

function getMockAdmin(): User {
  return {
    id: 'admin-001',
    telegram_id: 502621151,
    telegram_username: 'voodoo_cap',
    full_name: 'Преподаватель',
    role: 'teacher',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
  };
}

function getMockStudentWorks(studentId: string): StudentWork[] {
  return [
    {
      id: 'work-001',
      student_id: studentId,
      work_type_id: 'wt-001',
      title: 'Разработка системы управления учебными проектами на базе Telegram-бота',
      description: 'Выпускная квалификационная работа бакалавра',
      status: 'in_review',
      work_type: {
        id: 'wt-001',
        code: 'vkr_bachelor',
        name: 'ВКР (Бакалавр)',
        description: 'Выпускная квалификационная работа бакалавра',
        gost_requirements: 'ГОСТ 7.32-2017',
        max_volume_pages: 100,
        min_volume_pages: 60,
        deadline_days: 90,
        requires_ai_check: true,
      },
      teacher_comment: 'Хорошая работа, но нужно доработать раздел 3.',
      teacher_reviewed_at: '2024-11-15T14:30:00Z',
      ai_plagiarism_score: 85.5,
      ai_structure_score: 78.0,
      ai_formatting_score: 92.0,
      grade_classic: 4,
      grade_100: 82,
      grade_letter: 'B',
      deadline: '2024-12-20T23:59:00Z',
      submitted_at: '2024-11-10T09:00:00Z',
      created_at: '2024-09-15T10:00:00Z',
      updated_at: '2024-11-15T14:30:00Z',
      is_archived: false,
      files: [
        {
          id: 'f-001',
          work_id: 'work-001',
          filename: 'vkr_ivanov_v3.docx',
          original_name: 'ВКР_Иванов_Версия3.docx',
          mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          size_bytes: 2456000,
          storage_type: 'yandex_disk',
          yandex_file_path: '/DigitalTutor/ВКР_Бакалавр/ИС-101_Иванов/ВКР_Иванов_Версия3.docx',
          created_at: '2024-11-10T09:00:00Z',
        },
      ],
    },
    {
      id: 'work-002',
      student_id: studentId,
      work_type_id: 'wt-004',
      title: 'Методы машинного обучения в анализе текстов на русском языке',
      description: 'Научная статья для публикации в журнале',
      status: 'accepted',
      work_type: {
        id: 'wt-004',
        code: 'article',
        name: 'Научная статья',
        description: 'Научная статья для публикации',
        gost_requirements: 'Требования журнала',
        max_volume_pages: 20,
        min_volume_pages: 8,
        deadline_days: 60,
        requires_ai_check: true,
      },
      teacher_comment: 'Статья принята к публикации.',
      deadline: '2024-10-15T23:59:00Z',
      submitted_at: '2024-10-01T12:00:00Z',
      created_at: '2024-09-20T08:00:00Z',
      updated_at: '2024-10-10T16:00:00Z',
      is_archived: true,
      files: [
        {
          id: 'f-002',
          work_id: 'work-002',
          filename: 'article_ml_text.pdf',
          original_name: 'Статья_ML_тексты.pdf',
          mime_type: 'application/pdf',
          size_bytes: 890000,
          storage_type: 'yandex_disk',
          yandex_file_path: '/DigitalTutor/Статья/ИС-101_Иванов/Статья_ML_тексты.pdf',
          created_at: '2024-10-01T12:00:00Z',
        },
      ],
    },
    {
      id: 'work-003',
      student_id: studentId,
      work_type_id: 'wt-001',
      title: 'Сравнительный анализ NoSQL баз данных для веб-приложений',
      description: 'Курсовая работа по дисциплине "Базы данных"',
      status: 'revision_required',
      work_type: {
        id: 'wt-001',
        code: 'coursework',
        name: 'Курсовая работа',
        description: 'Курсовая работа по дисциплине',
        gost_requirements: 'ГОСТ 7.32-2017',
        max_volume_pages: 50,
        min_volume_pages: 25,
        deadline_days: 30,
        requires_ai_check: true,
      },
      teacher_comment: 'Необходимо добавить сравнительные таблицы и обновить список литературы. Смотрите комментарии в файле.',
      deadline: '2024-11-30T23:59:00Z',
      submitted_at: '2024-11-05T11:00:00Z',
      created_at: '2024-10-25T09:00:00Z',
      updated_at: '2024-11-12T10:00:00Z',
      is_archived: false,
      files: [
        {
          id: 'f-003',
          work_id: 'work-003',
          filename: 'coursework_nosql.docx',
          original_name: 'Курсовая_NoSQL_БД.docx',
          mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          size_bytes: 1250000,
          storage_type: 'yandex_disk',
          created_at: '2024-11-05T11:00:00Z',
        },
      ],
    },
  ];
}

function getMockCommunications(): Communication[] {
  return [
    {
      id: 'comm-001',
      work_id: 'work-001',
      student_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      from_user_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      to_user_id: 'admin-001',
      channel: 'telegram',
      message_type: 'text',
      content: 'Здравствуйте! Подскажите, пожалуйста, нужно ли добавлять тесты в третьей главе ВКР?',
      from_student: true,
      from_teacher: false,
      is_read: true,
      created_at: '2024-11-08T10:15:00Z',
      from_user: getMockStudent(),
    },
    {
      id: 'comm-002',
      work_id: 'work-001',
      student_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      from_user_id: 'admin-001',
      to_user_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      channel: 'telegram',
      message_type: 'text',
      content: 'Добрый день! Да, в разделе тестирования обязательно опишите методологию тестирования: модульные, интеграционные и приёмочные тесты. Приведите конкретные примеры тест-кейсов.',
      from_student: false,
      from_teacher: true,
      is_read: true,
      created_at: '2024-11-08T11:30:00Z',
      to_user: getMockStudent(),
    },
    {
      id: 'comm-003',
      work_id: 'work-001',
      student_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      from_user_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      to_user_id: 'admin-001',
      channel: 'telegram',
      message_type: 'text',
      content: 'Спасибо! А можно ли использовать фреймворк pytest? Или лучше что-то стандартное из Python unittest?',
      from_student: true,
      from_teacher: false,
      is_read: true,
      created_at: '2024-11-08T12:00:00Z',
      from_user: getMockStudent(),
    },
    {
      id: 'comm-004',
      work_id: 'work-001',
      student_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      from_user_id: 'admin-001',
      to_user_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      channel: 'telegram',
      message_type: 'text',
      content: 'pytest — отличный выбор. Обязательно опишите, почему выбрали именно его, и покажите примеры с фикстурами и параметризацией.',
      from_student: false,
      from_teacher: true,
      is_read: true,
      created_at: '2024-11-08T14:20:00Z',
      to_user: getMockStudent(),
    },
    {
      id: 'comm-005',
      work_id: 'work-003',
      student_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      from_user_id: 'admin-001',
      to_user_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      channel: 'telegram',
      message_type: 'system',
      content: 'Ваша курсовая работа "Сравнительный анализ NoSQL баз данных для веб-приложений" возвращена на доработку. Ознакомьтесь с комментариями преподавателя.',
      from_student: false,
      from_teacher: true,
      is_read: true,
      created_at: '2024-11-12T10:00:00Z',
      to_user: getMockStudent(),
    },
  ];
}

function getMockFiles(): FileRecord[] {
  return [
    {
      id: 'f-001',
      work_id: 'work-001',
      filename: 'vkr_ivanov_v3.docx',
      original_name: 'ВКР_Иванов_Версия3.docx',
      mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      size_bytes: 2456000,
      storage_type: 'yandex_disk',
      created_at: '2024-11-10T09:00:00Z',
    },
    {
      id: 'f-002',
      work_id: 'work-002',
      filename: 'article_ml_text.pdf',
      original_name: 'Статья_ML_тексты.pdf',
      mime_type: 'application/pdf',
      size_bytes: 890000,
      storage_type: 'yandex_disk',
      created_at: '2024-10-01T12:00:00Z',
    },
    {
      id: 'f-003',
      work_id: 'work-003',
      filename: 'coursework_nosql.docx',
      original_name: 'Курсовая_NoSQL_БД.docx',
      mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      size_bytes: 1250000,
      storage_type: 'yandex_disk',
      created_at: '2024-11-05T11:00:00Z',
    },
  ];
}

function getMockStudents(): User[] {
  return [
    getMockStudent(),
    {
      id: 's-002',
      telegram_id: 987654321,
      telegram_username: 'petrov_sergey',
      full_name: 'Петров Сергей Андреевич',
      role: 'Студент',
      group_name: 'ИС-101',
      course: 3,
      is_active: true,
      created_at: '2024-09-02T11:00:00Z',
    },
    {
      id: 's-003',
      telegram_id: 555666777,
      telegram_username: 'sidorova_anna',
      full_name: 'Сидорова Анна Дмитриевна',
      role: 'Студент',
      group_name: 'ИС-102',
      course: 4,
      is_active: true,
      created_at: '2024-09-01T14:00:00Z',
    },
    {
      id: 's-004',
      telegram_id: 111222333,
      telegram_username: 'kozlov_maxim',
      full_name: 'Козлов Максим Игоревич',
      role: 'Студент',
      group_name: 'ИС-101',
      course: 3,
      is_active: false,
      created_at: '2024-09-03T09:00:00Z',
    },
  ];
}

function getMockAllWorks(): StudentWork[] {
  const students = getMockStudents();
  return [
    ...getMockStudentWorks(students[0].id),
    {
      id: 'work-010',
      student_id: students[1].id,
      title: 'Разработка мобильного приложения для отслеживания успеваемости',
      status: 'submitted',
      work_type: {
        id: 'wt-001',
        code: 'vkr_bachelor',
        name: 'ВКР (Бакалавр)',
        max_volume_pages: 100,
        min_volume_pages: 60,
        requires_ai_check: true,
      },
      student: students[1],
      ai_plagiarism_score: 72.0,
      ai_structure_score: 85.0,
      ai_formatting_score: 68.0,
      deadline: '2024-12-25T23:59:00Z',
      submitted_at: '2024-11-18T08:00:00Z',
      created_at: '2024-09-20T10:00:00Z',
      updated_at: '2024-11-18T08:00:00Z',
      is_archived: false,
    },
    {
      id: 'work-011',
      student_id: students[2].id,
      title: 'Исследование методов оптимизации нейронных сетей',
      status: 'graded',
      work_type: {
        id: 'wt-003',
        code: 'vkr_master',
        name: 'ВКР (Магистр)',
        max_volume_pages: 120,
        min_volume_pages: 80,
        requires_ai_check: true,
      },
      student: students[2],
      ai_plagiarism_score: 91.0,
      ai_structure_score: 94.0,
      ai_formatting_score: 96.0,
      grade_classic: 5,
      grade_100: 95,
      grade_letter: 'A',
      grade_comment: 'Превосходная работа. Рекомендуется к публикации.',
      deadline: '2024-11-01T23:59:00Z',
      submitted_at: '2024-10-25T10:00:00Z',
      created_at: '2024-09-05T08:00:00Z',
      updated_at: '2024-10-28T16:00:00Z',
      is_archived: true,
    },
  ];
}

function getMockFileTree(): FileTreeNode[] {
  return [
    {
      name: 'ИС-101',
      path: '/ИС-101',
      type: 'folder',
      children: [
        {
          name: 'Иванов_И_И',
          path: '/ИС-101/Иванов_И_И',
          type: 'folder',
          children: [
            {
              name: 'ВКР',
              path: '/ИС-101/Иванов_И_И/ВКР',
              type: 'folder',
              children: [
                { name: 'ВКР_Иванов_Версия3.docx', path: '/ИС-101/Иванов_И_И/ВКР/ВКР_Иванов_Версия3.docx', type: 'file', size: 2456000, modified: '2024-11-10' },
                { name: 'ВКР_Иванов_Версия2.docx', path: '/ИС-101/Иванов_И_И/ВКР/ВКР_Иванов_Версия2.docx', type: 'file', size: 2300000, modified: '2024-10-28' },
                { name: 'ВКР_Иванов_Версия1.docx', path: '/ИС-101/Иванов_И_И/ВКР/ВКР_Иванов_Версия1.docx', type: 'file', size: 1800000, modified: '2024-10-15' },
              ],
            },
            {
              name: 'Курсовые',
              path: '/ИС-101/Иванов_И_И/Курсовые',
              type: 'folder',
              children: [
                { name: 'Курсовая_NoSQL_БД.docx', path: '/ИС-101/Иванов_И_И/Курсовые/Курсовая_NoSQL_БД.docx', type: 'file', size: 1250000, modified: '2024-11-05' },
              ],
            },
            {
              name: 'Статьи',
              path: '/ИС-101/Иванов_И_И/Статьи',
              type: 'folder',
              children: [
                { name: 'Статья_ML_тексты.pdf', path: '/ИС-101/Иванов_И_И/Статьи/Статья_ML_тексты.pdf', type: 'file', size: 890000, modified: '2024-10-01' },
              ],
            },
          ],
        },
        {
          name: 'Петров_С_А',
          path: '/ИС-101/Петров_С_А',
          type: 'folder',
          children: [
            {
              name: 'ВКР',
              path: '/ИС-101/Петров_С_А/ВКР',
              type: 'folder',
              children: [
                { name: 'ВКР_Петров_МобильноеПриложение.pdf', path: '/ИС-101/Петров_С_А/ВКР/ВКР_Петров_МобильноеПриложение.pdf', type: 'file', size: 3100000, modified: '2024-11-18' },
              ],
            },
          ],
        },
        {
          name: 'Козлов_М_И',
          path: '/ИС-101/Козлов_М_И',
          type: 'folder',
          children: [
            {
              name: 'ВКР',
              path: '/ИС-101/Козлов_М_И/ВКР',
              type: 'folder',
              children: [
                { name: 'ВКР_Козлов_Черновик.docx', path: '/ИС-101/Козлов_М_И/ВКР/ВКР_Козлов_Черновик.docx', type: 'file', size: 560000, modified: '2024-10-01' },
              ],
            },
          ],
        },
      ],
    },
    {
      name: 'ИС-102',
      path: '/ИС-102',
      type: 'folder',
      children: [
        {
          name: 'Сидорова_А_Д',
          path: '/ИС-102/Сидорова_А_Д',
          type: 'folder',
          children: [
            {
              name: 'ВКР_Магистр',
              path: '/ИС-102/Сидорова_А_Д/ВКР_Магистр',
              type: 'folder',
              children: [
                { name: 'Магистерская_Сидорова_Финал.pdf', path: '/ИС-102/Сидорова_А_Д/ВКР_Магистр/Магистерская_Сидорова_Финал.pdf', type: 'file', size: 4200000, modified: '2024-10-25' },
              ],
            },
          ],
        },
      ],
    },
  ];
}
