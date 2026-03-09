import { FormEvent, useEffect, useRef, useState } from 'react';

type TabId = 'library' | 'search' | 'people';
type AuthMode = 'login' | 'register';

type PhotoItem = {
  id: number;
  src: string;
};

type AuthUser = {
  id: number;
  username: string;
};

type AuthResponse = {
  authenticated: boolean;
  user?: AuthUser;
  message?: string;
  fieldErrors?: Record<string, string>;
};

const tabs: Array<{ id: TabId; label: string }> = [
  { id: 'library', label: 'Медиа' },
  { id: 'search', label: 'Поиск' },
  { id: 'people', label: 'Люди' },
];

const photos: PhotoItem[] = [
  { id: 1, src: '/demo/media/media-01.jpg' },
  { id: 2, src: '/demo/media/media-02.jpg' },
  { id: 3, src: '/demo/media/media-03.jpg' },
  { id: 4, src: '/demo/media/media-04.jpg' },
  { id: 5, src: '/demo/media/media-05.jpg' },
  { id: 6, src: '/demo/media/media-06.jpg' },
  { id: 7, src: '/demo/media/media-07.jpg' },
  { id: 8, src: '/demo/media/media-08.jpg' },
  { id: 9, src: '/demo/media/media-09.jpg' },
  { id: 10, src: '/demo/media/media-10.jpg' },
  { id: 11, src: '/demo/media/media-11.jpg' },
  { id: 12, src: '/demo/media/media-12.jpg' },
];

const people = [
  { id: 1, name: 'Анна', count: 28, photo: '/demo/people/person-01.jpg' },
  { id: 2, name: 'Человек 2', count: 14, photo: '/demo/people/person-02.jpg' },
  { id: 3, name: 'Максим', count: 19, photo: '/demo/people/person-03.jpg' },
  { id: 4, name: 'Человек 4', count: 8, photo: '/demo/people/person-04.jpg' },
  { id: 5, name: 'Елена', count: 11, photo: '/demo/people/person-05.jpg' },
  { id: 6, name: 'Человек 6', count: 6, photo: '/demo/people/person-06.jpg' },
];

const DEFAULT_AUTH_FIELDS = {
  username: '',
  password: '',
  passwordConfirm: '',
};

const AI_MODULE_INFO = {
  name: 'Модуль подключен',
  details: 'XPC / CUDA / RTX 5070 Ti',
};

function App() {
  const [authChecked, setAuthChecked] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authMode, setAuthMode] = useState<AuthMode>('login');
  const [authFields, setAuthFields] = useState(DEFAULT_AUTH_FIELDS);
  const [authMessage, setAuthMessage] = useState('');
  const [authErrors, setAuthErrors] = useState<Record<string, string>>({});
  const [authPending, setAuthPending] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>('library');
  const [animateView, setAnimateView] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    void loadCurrentUser();
  }, []);

  useEffect(() => {
    if (!user) {
      return;
    }

    setAnimateView(false);
    const frame = requestAnimationFrame(() => setAnimateView(true));
    return () => cancelAnimationFrame(frame);
  }, [activeTab, user]);

  async function loadCurrentUser() {
    try {
      const response = await fetch('/api/auth/me');
      if (!response.ok) {
        setUser(null);
        return;
      }

      const data = (await response.json()) as AuthResponse;
      setUser(data.user ?? null);
    } finally {
      setAuthChecked(true);
    }
  }

  function getCookie(name: string) {
    const cookie = document.cookie.split('; ').find((item) => item.startsWith(`${name}=`));
    return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : '';
  }

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthPending(true);
    setAuthMessage('');
    setAuthErrors({});

    const endpoint = authMode === 'login' ? '/api/auth/login' : '/api/auth/register';

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify(authFields),
      });

      const data = (await response.json()) as AuthResponse;
      if (!response.ok) {
        setAuthMessage(data.message ?? 'Не удалось выполнить авторизацию.');
        setAuthErrors(data.fieldErrors ?? {});
        return;
      }

      setUser(data.user ?? null);
      setAuthFields(DEFAULT_AUTH_FIELDS);
      setAuthMessage('');
      setAuthErrors({});
    } catch {
      setAuthMessage('Не удалось связаться с сервером авторизации.');
    } finally {
      setAuthPending(false);
    }
  }

  async function handleLogout() {
    await fetch('/api/auth/logout', {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });

    setUser(null);
    setAuthMode('login');
    setAuthFields(DEFAULT_AUTH_FIELDS);
    setAuthErrors({});
    setAuthMessage('');
  }

  function openPhotoPicker() {
    fileInputRef.current?.click();
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    setSelectedFiles(files.map((file) => file.name));
  }

  if (!authChecked) {
    return (
      <div className="auth-shell loading-shell">
        <div className="ambient ambient-left" />
        <div className="ambient ambient-right" />
        <div className="loading-badge">Проверяем сессию...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <AuthScreen
        mode={authMode}
        fields={authFields}
        pending={authPending}
        message={authMessage}
        errors={authErrors}
        onModeChange={(mode) => {
          setAuthMode(mode);
          setAuthMessage('');
          setAuthErrors({});
        }}
        onFieldChange={(name, value) => setAuthFields((current) => ({ ...current, [name]: value }))}
        onSubmit={submitAuth}
      />
    );
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />

      <header className={`topbar ${activeTab !== 'library' ? 'topbar-compact' : ''}`}>
        {activeTab === 'library' ? (
          <div className="hero-copy">
            <span className="eyebrow">Liquid Photos</span>
            <h1>Медиатека</h1>
            <p>Личная галерея, умный поиск и найденные люди в одном минималистичном интерфейсе.</p>
          </div>
        ) : activeTab === 'search' ? (
          <div className="hero-copy search-hero-copy">
            <span className="eyebrow">Liquid Photos</span>
          </div>
        ) : activeTab === 'people' ? (
          <div className="hero-copy people-hero-copy">
            <span className="eyebrow people-eyebrow">Liquid Photos</span>
            <h1>Люди</h1>
            <p>Лица, которые система нашла и сгруппировала по фотографиям в вашей медиатеке.</p>
          </div>
        ) : (
          <div className="topbar-spacer" />
        )}
        <div className="action-row">
          <div className="status-badge ai-badge">
            <span className="status-badge-label">{AI_MODULE_INFO.name}</span>
            <strong>{AI_MODULE_INFO.details}</strong>
          </div>
          <div className="user-badge">
            <span className="user-badge-label">Пользователь</span>
            <strong>{user.username}</strong>
          </div>
          <button className="glass-icon-button" aria-label="Открыть поиск" onClick={() => setActiveTab('search')}>
            <SearchIcon />
          </button>
          <button className="glass-icon-button primary" aria-label="Добавить фотографии" onClick={openPhotoPicker}>
            <PlusIcon />
          </button>
          <button className="glass-icon-button" aria-label="Выйти из аккаунта" onClick={() => void handleLogout()}>
            <LogoutIcon />
          </button>
        </div>
      </header>

      <input
        ref={fileInputRef}
        className="sr-only-control"
        type="file"
        accept="image/*"
        multiple
        onChange={handleFileChange}
      />

      <main className={`content ${animateView ? 'content-visible' : ''}`}>
        {activeTab === 'library' && <LibraryView />}
        {activeTab === 'search' && <SearchView searchQuery={searchQuery} setSearchQuery={setSearchQuery} />}
        {activeTab === 'people' && <PeopleView />}
      </main>

      {selectedFiles.length > 0 && (
        <div className="upload-toast" role="status" aria-live="polite">
          Выбрано {selectedFiles.length} фото
        </div>
      )}

      <nav className="tabbar" aria-label="Primary">
        <div className={`tab-highlight ${activeTab}`} />
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    </div>
  );
}

function AuthScreen({
  mode,
  fields,
  pending,
  message,
  errors,
  onModeChange,
  onFieldChange,
  onSubmit,
}: {
  mode: AuthMode;
  fields: typeof DEFAULT_AUTH_FIELDS;
  pending: boolean;
  message: string;
  errors: Record<string, string>;
  onModeChange: (mode: AuthMode) => void;
  onFieldChange: (name: keyof typeof DEFAULT_AUTH_FIELDS, value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const isRegister = mode === 'register';

  return (
    <div className="auth-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />
      <div className="auth-brand-row">
        <span className="eyebrow">Liquid Photos</span>
      </div>

      <section className="auth-layout">
        <div className="auth-card">
          <div className="auth-title-block">
            <h1>{isRegister ? 'Создайте аккаунт' : 'Вход в медиатеку'}</h1>
            <p>
              {isRegister
                ? 'Один аккаунт хранит вашу личную библиотеку, поиск по фото и найденных людей.'
                : 'Авторизуйтесь, чтобы открыть личную фотобиблиотеку, поиск и вкладку с найденными людьми.'}
            </p>
          </div>

          <div className="auth-card-header">
            <button className={`auth-mode-button ${mode === 'login' ? 'active' : ''}`} onClick={() => onModeChange('login')}>
              Вход
            </button>
            <button
              className={`auth-mode-button ${mode === 'register' ? 'active' : ''}`}
              onClick={() => onModeChange('register')}
            >
              Регистрация
            </button>
          </div>

          <form className="auth-form" onSubmit={onSubmit}>
            <label className="auth-field">
              <span>Имя пользователя</span>
              <input
                value={fields.username}
                onChange={(event) => onFieldChange('username', event.target.value)}
                placeholder="Например: egor"
                autoComplete="username"
              />
              {errors.username && <small>{errors.username}</small>}
            </label>

            <label className="auth-field">
              <span>Пароль</span>
              <input
                type="password"
                value={fields.password}
                onChange={(event) => onFieldChange('password', event.target.value)}
                placeholder="Не менее 8 символов"
                autoComplete={isRegister ? 'new-password' : 'current-password'}
              />
              {errors.password && <small>{errors.password}</small>}
            </label>

            {isRegister && (
              <label className="auth-field">
                <span>Повторите пароль</span>
                <input
                  type="password"
                  value={fields.passwordConfirm}
                  onChange={(event) => onFieldChange('passwordConfirm', event.target.value)}
                  placeholder="Повторите пароль"
                  autoComplete="new-password"
                />
                {errors.passwordConfirm && <small>{errors.passwordConfirm}</small>}
              </label>
            )}

            {message && <div className="auth-message">{message}</div>}

            <button className="auth-submit-button" type="submit" disabled={pending}>
              {pending ? 'Подождите...' : isRegister ? 'Создать аккаунт' : 'Войти'}
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}

function LibraryView() {
  return (
    <section className="library-grid" aria-label="Photo library">
      {photos.map((photo) => (
        <article key={photo.id} className="photo-card">
          <img src={photo.src} alt="" />
          <div className="photo-overlay" />
        </article>
      ))}
    </section>
  );
}

function SearchView({
  searchQuery,
  setSearchQuery,
}: {
  searchQuery: string;
  setSearchQuery: (value: string) => void;
}) {
  return (
    <section className="search-stage">
      <div className="search-intro">
        <h2>Поиск по фото</h2>
        <p>Опишите человека, объект, сцену или место на фотографии.</p>
      </div>

      <div className="search-composer">
        <div className="search-input-shell">
          <label className="sr-only-control" htmlFor="search-query">
            Поисковый запрос
          </label>
          <textarea
            id="search-query"
            className="search-textarea"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Например: девушка в очках рядом с машиной"
            rows={2}
          />

          <div className="search-toolbar">
            <button className="search-tool-button" aria-label="Добавить фильтр">
              <PlusIcon />
            </button>

            <div className="search-suggestions-inline">
              {['закат у моря', 'человек с собакой', 'ночной город'].map((item) => (
                <div key={item} className="glass-chip compact">
                  {item}
                </div>
              ))}
            </div>

            <button className="search-voice-button" aria-label="Голосовой поиск">
              <WaveIcon />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

function PeopleView() {
  return (
    <section className="panel-view">
      <div className="people-grid">
        {people.map((person) => (
          <article key={person.id} className="person-tile">
            <div className="person-portrait-shell">
              <img className="person-portrait" src={person.photo} alt={person.name} />
            </div>
            <span className="person-count">{person.count} фото</span>
            <h3>{person.name}</h3>
          </article>
        ))}
      </div>
    </section>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M10.5 4a6.5 6.5 0 1 0 4.03 11.6l4.44 4.44 1.06-1.06-4.44-4.44A6.5 6.5 0 0 0 10.5 4Zm0 1.5a5 5 0 1 1 0 10 5 5 0 0 1 0-10Z"
        fill="currentColor"
      />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M11.25 5h1.5v6.25H19v1.5h-6.25V19h-1.5v-6.25H5v-1.5h6.25V5Z" fill="currentColor" />
    </svg>
  );
}

function WaveIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M5.5 9.25a1 1 0 0 1 1 1v3.5a1 1 0 1 1-2 0v-3.5a1 1 0 0 1 1-1Zm4-2.25a1 1 0 0 1 1 1v8a1 1 0 1 1-2 0V8a1 1 0 0 1 1-1Zm4 3a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0v-2a1 1 0 0 1 1-1Zm4-4a1 1 0 0 1 1 1v10a1 1 0 1 1-2 0V7a1 1 0 0 1 1-1Z"
        fill="currentColor"
      />
    </svg>
  );
}

function LogoutIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M10.75 4.75a.75.75 0 0 1 0 1.5H8a1.75 1.75 0 0 0-1.75 1.75v8A1.75 1.75 0 0 0 8 17.75h2.75a.75.75 0 0 1 0 1.5H8A3.25 3.25 0 0 1 4.75 16V8A3.25 3.25 0 0 1 8 4.75h2.75Zm5.72 2.97a.75.75 0 0 1 1.06 0l3.72 3.72a.75.75 0 0 1 0 1.06l-3.72 3.72a.75.75 0 1 1-1.06-1.06l2.44-2.44H10a.75.75 0 0 1 0-1.5h8.91l-2.44-2.44a.75.75 0 0 1 0-1.06Z"
        fill="currentColor"
      />
    </svg>
  );
}

export default App;
