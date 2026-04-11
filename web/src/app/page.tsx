'use client';

import React, { useState, useCallback } from 'react';
import type { User, AppView } from '@/lib/types';
import { validateStudentCode, validateAdminCode } from '@/lib/api';
import LandingView from '@/components/LandingView';
import StudentLoginView from '@/components/StudentLoginView';
import AdminLoginView from '@/components/AdminLoginView';
import StudentDashboard from '@/components/StudentDashboard';
import AdminDashboard from '@/components/AdminDashboard';

export default function Home() {
  const [view, setView] = useState<AppView>('landing');
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  const handleStudentLogin = useCallback(async (code: string) => {
    setIsLoading(true);
    setError(undefined);
    try {
      const response = await validateStudentCode(code);
      if (response.success && response.user) {
        setUser(response.user);
        setView('student-dashboard');
      } else {
        setError(response.error || 'Ошибка входа');
      }
    } catch {
      setError('Не удалось подключиться к серверу');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleAdminLogin = useCallback(async (code: string) => {
    setIsLoading(true);
    setError(undefined);
    try {
      const response = await validateAdminCode(code);
      if (response.success && response.user) {
        setUser(response.user);
        setView('admin-dashboard');
      } else {
        setError(response.error || 'Ошибка входа');
      }
    } catch {
      setError('Не удалось подключиться к серверу');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleLogout = useCallback(() => {
    setUser(null);
    setView('landing');
    setError(undefined);
  }, []);

  const renderView = () => {
    switch (view) {
      case 'landing':
        return (
          <LandingView
            onStudentLogin={() => { setView('student-login'); setError(undefined); }}
            onAdminLogin={() => { setView('admin-login'); setError(undefined); }}
          />
        );
      case 'student-login':
        return (
          <StudentLoginView
            onLogin={handleStudentLogin}
            onBack={() => { setView('landing'); setError(undefined); }}
            isLoading={isLoading}
            error={error}
          />
        );
      case 'admin-login':
        return (
          <AdminLoginView
            onLogin={handleAdminLogin}
            onBack={() => { setView('landing'); setError(undefined); }}
            isLoading={isLoading}
            error={error}
          />
        );
      case 'student-dashboard':
        return user ? (
          <StudentDashboard user={user} onLogout={handleLogout} />
        ) : null;
      case 'admin-dashboard':
        return user ? (
          <AdminDashboard user={user} onLogout={handleLogout} />
        ) : null;
      default:
        return null;
    }
  };

  return (
    <main>
      {renderView()}
    </main>
  );
}
