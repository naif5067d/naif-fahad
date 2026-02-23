/**
 * مكتبة أصوات دار الكود
 * DAR AL CODE Sound Library
 * 
 * 20 نغمة ترحيبية + 20 نغمة إشعارات
 * مصممة لمكتب هندسي - هادئة، أنيقة، تلامس القلوب
 */

let audioContext = null;

const getAudioContext = () => {
  if (!audioContext || audioContext.state === 'closed') {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioContext.state === 'suspended') {
    audioContext.resume();
  }
  return audioContext;
};

// ==================== الأدوات الموسيقية ====================

const playTone = (ctx, freq, startTime, duration, volume = 0.1, type = 'sine') => {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  const filter = ctx.createBiquadFilter();
  
  filter.type = 'lowpass';
  filter.frequency.value = 2500;
  filter.Q.value = 0.7;
  
  osc.connect(filter);
  filter.connect(gain);
  gain.connect(ctx.destination);
  
  osc.type = type;
  osc.frequency.setValueAtTime(freq, startTime);
  
  // تدرج ناعم
  gain.gain.setValueAtTime(0, startTime);
  gain.gain.linearRampToValueAtTime(volume, startTime + 0.02);
  gain.gain.setValueAtTime(volume, startTime + duration * 0.7);
  gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
  
  osc.start(startTime);
  osc.stop(startTime + duration);
};

const playChord = (ctx, freqs, startTime, duration, volume = 0.08) => {
  freqs.forEach(freq => playTone(ctx, freq, startTime, duration, volume / freqs.length));
};

// ==================== الترددات الموسيقية ====================
const NOTES = {
  C3: 130.81, D3: 146.83, E3: 164.81, F3: 174.61, G3: 196.00, A3: 220.00, B3: 246.94,
  C4: 261.63, D4: 293.66, E4: 329.63, F4: 349.23, G4: 392.00, A4: 440.00, B4: 493.88,
  C5: 523.25, D5: 587.33, E5: 659.25, F5: 698.46, G5: 783.99, A5: 880.00, B5: 987.77,
  C6: 1046.50, D6: 1174.66, E6: 1318.51
};

// ==================== 20 نغمة ترحيبية ====================

export const WELCOME_SOUNDS = {
  // 1. دار الكود الكلاسيكية - D-A-C
  dar_classic: {
    name_ar: 'دار الكود الكلاسيكية',
    name_en: 'Dar Al Code Classic',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      // D-A-C (دار - الـ - كود)
      playTone(ctx, NOTES.D4, now, 0.3, 0.12);
      playTone(ctx, NOTES.A4, now + 0.25, 0.3, 0.14);
      playTone(ctx, NOTES.C5, now + 0.5, 0.5, 0.12);
      playChord(ctx, [NOTES.D4, NOTES.A4, NOTES.C5], now + 0.9, 0.8, 0.08);
    }
  },

  // 2. الصباح الهندسي
  morning_engineer: {
    name_ar: 'الصباح الهندسي',
    name_en: 'Engineer Morning',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.C4, now, 0.2, 0.1);
      playTone(ctx, NOTES.E4, now + 0.15, 0.2, 0.12);
      playTone(ctx, NOTES.G4, now + 0.3, 0.2, 0.14);
      playTone(ctx, NOTES.C5, now + 0.45, 0.4, 0.12);
      playTone(ctx, NOTES.E5, now + 0.7, 0.5, 0.08);
    }
  },

  // 3. همسة الترحيب
  gentle_whisper: {
    name_ar: 'همسة الترحيب',
    name_en: 'Gentle Whisper',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playChord(ctx, [NOTES.C4, NOTES.E4, NOTES.G4], now, 0.6, 0.06);
      playChord(ctx, [NOTES.D4, NOTES.F4, NOTES.A4], now + 0.5, 0.6, 0.07);
      playChord(ctx, [NOTES.C4, NOTES.E4, NOTES.G4, NOTES.C5], now + 1, 0.8, 0.06);
    }
  },

  // 4. النجم الصاعد
  rising_star: {
    name_ar: 'النجم الصاعد',
    name_en: 'Rising Star',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      [NOTES.G3, NOTES.C4, NOTES.E4, NOTES.G4, NOTES.C5].forEach((freq, i) => {
        playTone(ctx, freq, now + i * 0.12, 0.25, 0.1);
      });
      playTone(ctx, NOTES.E5, now + 0.7, 0.6, 0.08);
    }
  },

  // 5. الفجر الذهبي
  golden_dawn: {
    name_ar: 'الفجر الذهبي',
    name_en: 'Golden Dawn',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playChord(ctx, [NOTES.D4, NOTES.A4], now, 0.4, 0.08);
      playChord(ctx, [NOTES.E4, NOTES.B4], now + 0.35, 0.4, 0.09);
      playChord(ctx, [NOTES.D4, NOTES.F4, NOTES.A4, NOTES.D5], now + 0.7, 0.7, 0.07);
    }
  },

  // 6. نسيم البحر
  sea_breeze: {
    name_ar: 'نسيم البحر',
    name_en: 'Sea Breeze',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.E4, now, 0.5, 0.08, 'triangle');
      playTone(ctx, NOTES.G4, now + 0.3, 0.5, 0.09, 'triangle');
      playTone(ctx, NOTES.B4, now + 0.6, 0.5, 0.1, 'triangle');
      playTone(ctx, NOTES.E5, now + 0.9, 0.7, 0.08, 'triangle');
    }
  },

  // 7. القلب الدافئ
  warm_heart: {
    name_ar: 'القلب الدافئ',
    name_en: 'Warm Heart',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playChord(ctx, [NOTES.F4, NOTES.A4, NOTES.C5], now, 0.5, 0.08);
      playChord(ctx, [NOTES.G4, NOTES.B4, NOTES.D5], now + 0.4, 0.5, 0.09);
      playChord(ctx, [NOTES.F4, NOTES.A4, NOTES.C5, NOTES.F5], now + 0.8, 0.7, 0.07);
    }
  },

  // 8. الأمل المشرق
  bright_hope: {
    name_ar: 'الأمل المشرق',
    name_en: 'Bright Hope',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.C5, now, 0.2, 0.1);
      playTone(ctx, NOTES.E5, now + 0.15, 0.2, 0.11);
      playTone(ctx, NOTES.G5, now + 0.3, 0.3, 0.12);
      playChord(ctx, [NOTES.C5, NOTES.E5, NOTES.G5, NOTES.C6], now + 0.55, 0.8, 0.08);
    }
  },

  // 9. السلام الداخلي
  inner_peace: {
    name_ar: 'السلام الداخلي',
    name_en: 'Inner Peace',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playChord(ctx, [NOTES.G3, NOTES.D4, NOTES.G4], now, 0.8, 0.06);
      playChord(ctx, [NOTES.C4, NOTES.E4, NOTES.G4], now + 0.7, 0.9, 0.06);
    }
  },

  // 10. الطموح
  ambition: {
    name_ar: 'الطموح',
    name_en: 'Ambition',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      [NOTES.C4, NOTES.D4, NOTES.E4, NOTES.G4, NOTES.C5].forEach((freq, i) => {
        playTone(ctx, freq, now + i * 0.1, 0.2, 0.09);
      });
      playChord(ctx, [NOTES.C4, NOTES.E4, NOTES.G4, NOTES.C5], now + 0.6, 0.6, 0.07);
    }
  },

  // 11. الإلهام
  inspiration: {
    name_ar: 'الإلهام',
    name_en: 'Inspiration',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.A4, now, 0.25, 0.1);
      playTone(ctx, NOTES.C5, now + 0.2, 0.25, 0.11);
      playTone(ctx, NOTES.E5, now + 0.4, 0.35, 0.12);
      playChord(ctx, [NOTES.A4, NOTES.C5, NOTES.E5], now + 0.7, 0.6, 0.08);
    }
  },

  // 12. اللمسة الناعمة
  soft_touch: {
    name_ar: 'اللمسة الناعمة',
    name_en: 'Soft Touch',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playChord(ctx, [NOTES.E4, NOTES.G4, NOTES.B4], now, 0.5, 0.05);
      playChord(ctx, [NOTES.F4, NOTES.A4, NOTES.C5], now + 0.4, 0.5, 0.06);
      playChord(ctx, [NOTES.E4, NOTES.G4, NOTES.B4, NOTES.E5], now + 0.8, 0.6, 0.05);
    }
  },

  // 13. البداية الجديدة
  new_beginning: {
    name_ar: 'البداية الجديدة',
    name_en: 'New Beginning',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.G4, now, 0.15, 0.08);
      playTone(ctx, NOTES.A4, now + 0.12, 0.15, 0.09);
      playTone(ctx, NOTES.B4, now + 0.24, 0.15, 0.1);
      playTone(ctx, NOTES.C5, now + 0.36, 0.15, 0.11);
      playTone(ctx, NOTES.D5, now + 0.48, 0.2, 0.12);
      playChord(ctx, [NOTES.G4, NOTES.B4, NOTES.D5, NOTES.G5], now + 0.65, 0.7, 0.08);
    }
  },

  // 14. الهدوء
  serenity: {
    name_ar: 'الهدوء',
    name_en: 'Serenity',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playChord(ctx, [NOTES.C4, NOTES.G4], now, 0.7, 0.05);
      playChord(ctx, [NOTES.E4, NOTES.B4], now + 0.5, 0.7, 0.06);
      playChord(ctx, [NOTES.C4, NOTES.E4, NOTES.G4], now + 1, 0.8, 0.05);
    }
  },

  // 15. التألق
  brilliance: {
    name_ar: 'التألق',
    name_en: 'Brilliance',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      [NOTES.E5, NOTES.G5, NOTES.B5, NOTES.E6].forEach((freq, i) => {
        playTone(ctx, freq, now + i * 0.08, 0.2, 0.08);
      });
      playChord(ctx, [NOTES.E4, NOTES.G4, NOTES.B4, NOTES.E5], now + 0.4, 0.7, 0.06);
    }
  },

  // 16. المعمار
  architecture: {
    name_ar: 'المعمار',
    name_en: 'Architecture',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      // بناء متدرج كالهندسة المعمارية
      playTone(ctx, NOTES.C3, now, 0.3, 0.08);
      playTone(ctx, NOTES.G3, now + 0.2, 0.3, 0.09);
      playTone(ctx, NOTES.C4, now + 0.4, 0.3, 0.1);
      playTone(ctx, NOTES.E4, now + 0.6, 0.3, 0.11);
      playChord(ctx, [NOTES.C4, NOTES.E4, NOTES.G4, NOTES.C5], now + 0.85, 0.7, 0.08);
    }
  },

  // 17. الريادة
  leadership: {
    name_ar: 'الريادة',
    name_en: 'Leadership',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playChord(ctx, [NOTES.D4, NOTES.F4, NOTES.A4], now, 0.3, 0.09);
      playChord(ctx, [NOTES.E4, NOTES.G4, NOTES.B4], now + 0.25, 0.3, 0.1);
      playChord(ctx, [NOTES.D4, NOTES.F4, NOTES.A4, NOTES.D5], now + 0.5, 0.6, 0.08);
    }
  },

  // 18. الإنجاز
  achievement: {
    name_ar: 'الإنجاز',
    name_en: 'Achievement',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.C4, now, 0.15, 0.1);
      playTone(ctx, NOTES.E4, now + 0.1, 0.15, 0.11);
      playTone(ctx, NOTES.G4, now + 0.2, 0.15, 0.12);
      playTone(ctx, NOTES.C5, now + 0.3, 0.2, 0.13);
      playTone(ctx, NOTES.E5, now + 0.45, 0.3, 0.11);
      playTone(ctx, NOTES.G5, now + 0.65, 0.5, 0.09);
    }
  },

  // 19. الانتماء
  belonging: {
    name_ar: 'الانتماء',
    name_en: 'Belonging',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      // نغمة دافئة تعبر عن الانتماء
      playChord(ctx, [NOTES.F3, NOTES.C4, NOTES.F4], now, 0.5, 0.06);
      playChord(ctx, [NOTES.G3, NOTES.D4, NOTES.G4], now + 0.4, 0.5, 0.07);
      playChord(ctx, [NOTES.F3, NOTES.A3, NOTES.C4, NOTES.F4], now + 0.8, 0.7, 0.06);
    }
  },

  // 20. دار الكود الذهبية
  dar_golden: {
    name_ar: 'دار الكود الذهبية',
    name_en: 'Dar Al Code Golden',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      // D-A-R  A-L  C-O-D-E
      playTone(ctx, NOTES.D4, now, 0.2, 0.1);
      playTone(ctx, NOTES.A4, now + 0.18, 0.2, 0.11);
      playTone(ctx, NOTES.D5, now + 0.36, 0.25, 0.12);
      // فاصل
      playTone(ctx, NOTES.A4, now + 0.55, 0.15, 0.1);
      // C-O-D-E
      playTone(ctx, NOTES.C5, now + 0.7, 0.15, 0.11);
      playTone(ctx, NOTES.E5, now + 0.85, 0.15, 0.12);
      playTone(ctx, NOTES.D5, now + 1, 0.15, 0.11);
      playTone(ctx, NOTES.E5, now + 1.15, 0.3, 0.1);
      // ختام
      playChord(ctx, [NOTES.D4, NOTES.A4, NOTES.D5], now + 1.4, 0.7, 0.08);
    }
  }
};


// ==================== 20 نغمة إشعارات ====================

export const NOTIFICATION_SOUNDS = {
  // 1. النقرة الناعمة
  soft_click: {
    name_ar: 'النقرة الناعمة',
    name_en: 'Soft Click',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.E5, now, 0.1, 0.12);
      playTone(ctx, NOTES.G5, now + 0.08, 0.15, 0.1);
    }
  },

  // 2. الجرس الكريستالي
  crystal_bell: {
    name_ar: 'الجرس الكريستالي',
    name_en: 'Crystal Bell',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.C6, now, 0.15, 0.1);
      playTone(ctx, NOTES.E5, now + 0.1, 0.2, 0.08);
    }
  },

  // 3. القطرة
  droplet: {
    name_ar: 'القطرة',
    name_en: 'Droplet',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.G5, now, 0.08, 0.12);
      playTone(ctx, NOTES.C5, now + 0.06, 0.15, 0.08);
    }
  },

  // 4. النغمة المزدوجة
  double_tone: {
    name_ar: 'النغمة المزدوجة',
    name_en: 'Double Tone',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.E5, now, 0.1, 0.1);
      playTone(ctx, NOTES.A5, now + 0.12, 0.12, 0.11);
    }
  },

  // 5. الهمسة
  whisper: {
    name_ar: 'الهمسة',
    name_en: 'Whisper',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playChord(ctx, [NOTES.C5, NOTES.E5], now, 0.15, 0.06);
    }
  },

  // 6. النجمة
  star: {
    name_ar: 'النجمة',
    name_en: 'Star',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.A5, now, 0.08, 0.12);
      playTone(ctx, NOTES.E5, now + 0.06, 0.08, 0.1);
      playTone(ctx, NOTES.A5, now + 0.12, 0.12, 0.08);
    }
  },

  // 7. الفقاعة
  bubble: {
    name_ar: 'الفقاعة',
    name_en: 'Bubble',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.C5, now, 0.05, 0.1);
      playTone(ctx, NOTES.E5, now + 0.04, 0.05, 0.11);
      playTone(ctx, NOTES.G5, now + 0.08, 0.08, 0.09);
    }
  },

  // 8. الإيقاع الخفيف
  light_beat: {
    name_ar: 'الإيقاع الخفيف',
    name_en: 'Light Beat',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.G4, now, 0.06, 0.1);
      playTone(ctx, NOTES.G5, now + 0.08, 0.1, 0.12);
    }
  },

  // 9. الأكورد الصغير
  mini_chord: {
    name_ar: 'الأكورد الصغير',
    name_en: 'Mini Chord',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playChord(ctx, [NOTES.C5, NOTES.E5, NOTES.G5], now, 0.12, 0.08);
    }
  },

  // 10. الصدى
  echo: {
    name_ar: 'الصدى',
    name_en: 'Echo',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.E5, now, 0.1, 0.12);
      playTone(ctx, NOTES.E5, now + 0.12, 0.08, 0.06);
      playTone(ctx, NOTES.E5, now + 0.22, 0.06, 0.03);
    }
  },

  // 11. البريق
  sparkle: {
    name_ar: 'البريق',
    name_en: 'Sparkle',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.G5, now, 0.05, 0.1);
      playTone(ctx, NOTES.C6, now + 0.05, 0.08, 0.12);
      playTone(ctx, NOTES.E6, now + 0.1, 0.1, 0.08);
    }
  },

  // 12. النبضة
  pulse: {
    name_ar: 'النبضة',
    name_en: 'Pulse',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.A4, now, 0.08, 0.1);
      playTone(ctx, NOTES.A5, now + 0.1, 0.12, 0.12);
    }
  },

  // 13. الرنين
  ring: {
    name_ar: 'الرنين',
    name_en: 'Ring',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.E5, now, 0.2, 0.1, 'triangle');
      playTone(ctx, NOTES.B5, now + 0.05, 0.15, 0.08, 'triangle');
    }
  },

  // 14. اللمعة
  glint: {
    name_ar: 'اللمعة',
    name_en: 'Glint',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.D5, now, 0.06, 0.11);
      playTone(ctx, NOTES.A5, now + 0.05, 0.1, 0.12);
    }
  },

  // 15. التنبيه الهادئ
  calm_alert: {
    name_ar: 'التنبيه الهادئ',
    name_en: 'Calm Alert',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playChord(ctx, [NOTES.G4, NOTES.B4, NOTES.D5], now, 0.15, 0.07);
    }
  },

  // 16. الموجة
  wave: {
    name_ar: 'الموجة',
    name_en: 'Wave',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.C5, now, 0.1, 0.08, 'triangle');
      playTone(ctx, NOTES.E5, now + 0.08, 0.1, 0.1, 'triangle');
      playTone(ctx, NOTES.C5, now + 0.16, 0.1, 0.06, 'triangle');
    }
  },

  // 17. النقر المزدوج
  double_tap: {
    name_ar: 'النقر المزدوج',
    name_en: 'Double Tap',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.F5, now, 0.05, 0.1);
      playTone(ctx, NOTES.F5, now + 0.08, 0.05, 0.1);
    }
  },

  // 18. الإشراق
  glow: {
    name_ar: 'الإشراق',
    name_en: 'Glow',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playChord(ctx, [NOTES.D5, NOTES.F5, NOTES.A5], now, 0.18, 0.08);
    }
  },

  // 19. التذكير
  reminder: {
    name_ar: 'التذكير',
    name_en: 'Reminder',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      playTone(ctx, NOTES.G5, now, 0.1, 0.1);
      playTone(ctx, NOTES.E5, now + 0.1, 0.1, 0.1);
      playTone(ctx, NOTES.G5, now + 0.2, 0.12, 0.08);
    }
  },

  // 20. دار الكود - إشعار
  dar_notification: {
    name_ar: 'دار الكود',
    name_en: 'Dar Al Code',
    play: () => {
      const ctx = getAudioContext();
      const now = ctx.currentTime;
      // D-A-C مختصرة
      playTone(ctx, NOTES.D5, now, 0.08, 0.11);
      playTone(ctx, NOTES.A5, now + 0.07, 0.08, 0.12);
      playTone(ctx, NOTES.C6, now + 0.14, 0.12, 0.1);
    }
  }
};


// ==================== تشغيل الأصوات ====================

export const playWelcomeSound = (soundKey = 'dar_classic') => {
  try {
    const sound = WELCOME_SOUNDS[soundKey];
    if (sound && sound.play) {
      sound.play();
    }
  } catch (e) {
    console.log('Audio not supported:', e);
  }
};

export const playNotificationSound = (soundKey = 'dar_notification') => {
  try {
    const sound = NOTIFICATION_SOUNDS[soundKey];
    if (sound && sound.play) {
      sound.play();
    }
  } catch (e) {
    console.log('Audio not supported:', e);
  }
};

// قائمة الأصوات للعرض
export const getWelcomeSoundsList = () => {
  return Object.entries(WELCOME_SOUNDS).map(([key, value]) => ({
    key,
    name_ar: value.name_ar,
    name_en: value.name_en
  }));
};

export const getNotificationSoundsList = () => {
  return Object.entries(NOTIFICATION_SOUNDS).map(([key, value]) => ({
    key,
    name_ar: value.name_ar,
    name_en: value.name_en
  }));
};

export default {
  WELCOME_SOUNDS,
  NOTIFICATION_SOUNDS,
  playWelcomeSound,
  playNotificationSound,
  getWelcomeSoundsList,
  getNotificationSoundsList
};
