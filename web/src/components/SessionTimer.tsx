'use client';

import React, { useState, useEffect, useCallback } from 'react';

interface SessionTimerProps {
  startTime: number;
  onSessionEnd: () => void;
}

export default function SessionTimer({ startTime, onSessionEnd }: SessionTimerProps) {
  const SESSION_DURATION = 5400; // 1.5 hours in seconds

  const getTimeLeft = useCallback(() => {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    return Math.max(0, SESSION_DURATION - elapsed);
  }, [startTime]);

  const [timeLeft, setTimeLeft] = useState(getTimeLeft);

  useEffect(() => {
    const interval = setInterval(() => {
      const remaining = getTimeLeft();
      setTimeLeft(remaining);

      if (remaining <= 0) {
        clearInterval(interval);
        onSessionEnd();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [getTimeLeft, onSessionEnd]);

  const formatTime = (seconds: number): string => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  let timerClass = 'dt-header__timer';
  if (timeLeft < 300) {
    timerClass += ' dt-header__timer--danger';
  } else if (timeLeft < 900) {
    timerClass += ' dt-header__timer--warning';
  }

  return (
    <span className={timerClass} title="Оставшееся время сессии">
      {formatTime(timeLeft)}
    </span>
  );
}
