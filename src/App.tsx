import { FormEvent, useEffect, useRef, useState } from 'react';

type TabId = 'library' | 'search' | 'people';
type AuthMode = 'login' | 'register';

type PhotoItem = {
  id: number;
  src: string;
  originalFilename: string;
  processingStatus: string;
};

type SearchResultItem = PhotoItem & {
  score: number;
  scorePercent: number;
};

type PersonItem = {
  id: number;
  displayName: string;
  fallbackName: string;
  previewUrl: string;
  faceCount: number;
  photoCount: number;
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

type PhotoApiItem = {
  id: number;
  url: string;
  originalFilename: string;
  processingStatus: string;
};

type PhotoListResponse = {
  photos: PhotoApiItem[];
};

type PhotoUploadResponse = {
  message?: string;
  photos?: PhotoApiItem[];
  invalidFiles?: string[];
};

type PhotoDeleteResponse = {
  message?: string;
  photoId?: number;
};

type PersonApiItem = {
  id: number;
  displayName: string;
  fallbackName: string;
  previewUrl: string;
  faceCount: number;
  photoCount: number;
};

type PeopleListResponse = {
  people: PersonApiItem[];
  message?: string;
};

type PersonPhotosResponse = {
  person: {
    id: number;
    displayName: string;
  };
  photos: PhotoApiItem[];
  message?: string;
};

type PersonRenameResponse = {
  person?: {
    id: number;
    displayName: string;
  };
  message?: string;
};

type AiStatusResponse = {
  enabled: boolean;
  state: string;
  summary: string;
  details: string;
  reason: string;
};

type SearchResponse = {
  query: string;
  photos: Array<{
    id: number;
    url: string;
    originalFilename: string;
    processingStatus: string;
    score: number;
    scorePercent: number;
  }>;
  topK: number;
  totalIndexedPhotos: number;
  skippedPhotos?: number;
  message?: string;
};

const tabs: Array<{ id: TabId; label: string }> = [
  { id: 'library', label: 'Медиа' },
  { id: 'search', label: 'Поиск' },
  { id: 'people', label: 'Люди' },
];

const DEFAULT_AUTH_FIELDS = {
  username: '',
  password: '',
  passwordConfirm: '',
};

const ALLOWED_UPLOAD_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'];

async function readJsonSafely<T>(response: Response): Promise<T | null> {
  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.includes('application/json')) {
    return null;
  }

  try {
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

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
  const [photos, setPhotos] = useState<PhotoItem[]>([]);
  const [photosLoading, setPhotosLoading] = useState(false);
  const [searchPending, setSearchPending] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [searchMessage, setSearchMessage] = useState('');
  const [hasSearched, setHasSearched] = useState(false);
  const [people, setPeople] = useState<PersonItem[]>([]);
  const [peopleLoading, setPeopleLoading] = useState(false);
  const [peopleMessage, setPeopleMessage] = useState('');
  const [selectedPersonId, setSelectedPersonId] = useState<number | null>(null);
  const [personPhotos, setPersonPhotos] = useState<PhotoItem[]>([]);
  const [personPhotosLoading, setPersonPhotosLoading] = useState(false);
  const [personPhotosMessage, setPersonPhotosMessage] = useState('');
  const [personRenameDraft, setPersonRenameDraft] = useState('');
  const [personRenamePending, setPersonRenamePending] = useState(false);
  const [uploadPending, setUploadPending] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [photoMenu, setPhotoMenu] = useState<{ photoId: number; x: number; y: number } | null>(null);
  const [aiStatus, setAiStatus] = useState<AiStatusResponse>({
    enabled: false,
    state: 'loading',
    summary: 'Проверяем модуль',
    details: 'Запрашиваем текущее состояние AI-модуля',
    reason: '',
  });
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const photoMenuRef = useRef<HTMLDivElement | null>(null);
  const toastTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    void loadCurrentUser();
    void loadAiStatus();
  }, []);

  useEffect(() => {
    if (!user) {
      setPhotos([]);
      setSearchResults([]);
      setSearchMessage('');
      setHasSearched(false);
      setPeople([]);
      setPeopleMessage('');
      setSelectedPersonId(null);
      setPersonPhotos([]);
      setPersonPhotosMessage('');
      setPersonRenameDraft('');
      return;
    }

    void loadPhotos();
    void loadPeople();
  }, [user]);

  useEffect(() => {
    if (!user) {
      return;
    }

    setAnimateView(false);
    const frame = requestAnimationFrame(() => setAnimateView(true));
    return () => cancelAnimationFrame(frame);
  }, [activeTab, user]);

  useEffect(() => {
    return () => {
      if (toastTimeoutRef.current !== null) {
        window.clearTimeout(toastTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!photoMenu) {
      return;
    }

    function closePhotoMenu(event: Event) {
      if (event.target instanceof Node && photoMenuRef.current?.contains(event.target)) {
        return;
      }

      setPhotoMenu(null);
    }

    window.addEventListener('mousedown', closePhotoMenu);
    window.addEventListener('scroll', closePhotoMenu, true);

    return () => {
      window.removeEventListener('mousedown', closePhotoMenu);
      window.removeEventListener('scroll', closePhotoMenu, true);
    };
  }, [photoMenu]);

  useEffect(() => {
    if (!user || selectedPersonId === null) {
      setPersonPhotos([]);
      setPersonPhotosMessage('');
      return;
    }

    void loadPersonPhotos(selectedPersonId);
  }, [selectedPersonId, user]);

  useEffect(() => {
    const selectedPerson = people.find((person) => person.id === selectedPersonId) ?? null;
    setPersonRenameDraft(selectedPerson?.displayName ?? '');
  }, [people, selectedPersonId]);

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

  async function loadAiStatus() {
    try {
      const response = await fetch('/api/ai/status');
      const data = await readJsonSafely<AiStatusResponse>(response);
      if (!response.ok || !data) {
        setAiStatus({
          enabled: false,
          state: 'error',
          summary: 'Статус недоступен',
          details: 'Не удалось получить состояние AI-модуля',
          reason: 'API статуса вернул ошибку.',
        });
        return;
      }

      setAiStatus(data);
    } catch {
      setAiStatus({
        enabled: false,
        state: 'error',
        summary: 'Статус недоступен',
        details: 'Нет ответа от AI status API',
        reason: 'Не удалось выполнить запрос состояния AI-модуля.',
      });
    }
  }

  function mapPhoto(item: PhotoApiItem): PhotoItem {
    return {
      id: item.id,
      src: item.url,
      originalFilename: item.originalFilename,
      processingStatus: item.processingStatus,
    };
  }

  function mapSearchResult(item: SearchResponse['photos'][number]): SearchResultItem {
    return {
      id: item.id,
      src: item.url,
      originalFilename: item.originalFilename,
      processingStatus: item.processingStatus,
      score: item.score,
      scorePercent: item.scorePercent,
    };
  }

  function mapPerson(item: PersonApiItem): PersonItem {
    return {
      id: item.id,
      displayName: item.displayName,
      fallbackName: item.fallbackName,
      previewUrl: item.previewUrl,
      faceCount: item.faceCount,
      photoCount: item.photoCount,
    };
  }

  async function loadPhotos() {
    setPhotosLoading(true);
    try {
      const response = await fetch('/api/photos');
      if (!response.ok) {
        setPhotos([]);
        return;
      }

      const data = (await response.json()) as PhotoListResponse;
      setPhotos((data.photos ?? []).map(mapPhoto));
    } finally {
      setPhotosLoading(false);
    }
  }

  async function loadPeople() {
    setPeopleLoading(true);
    try {
      const response = await fetch('/api/people');
      const data = await readJsonSafely<PeopleListResponse>(response);
      if (!response.ok || !data) {
        setPeople([]);
        setPeopleMessage(data?.message ?? 'Не удалось загрузить список людей.');
        setSelectedPersonId(null);
        return;
      }

      const mappedPeople = (data.people ?? []).map(mapPerson);
      setPeople(mappedPeople);
      setPeopleMessage(data.message ?? '');
      setSelectedPersonId((current) => {
        if (current !== null && mappedPeople.some((person) => person.id === current)) {
          return current;
        }
        return mappedPeople[0]?.id ?? null;
      });
    } catch {
      setPeople([]);
      setPeopleMessage('Не удалось связаться с API людей.');
      setSelectedPersonId(null);
    } finally {
      setPeopleLoading(false);
    }
  }

  async function loadPersonPhotos(personId: number) {
    setPersonPhotosLoading(true);
    try {
      const response = await fetch(`/api/people/${personId}/photos`);
      const data = await readJsonSafely<PersonPhotosResponse>(response);
      if (!response.ok || !data) {
        setPersonPhotos([]);
        setPersonPhotosMessage(data?.message ?? 'Не удалось загрузить фотографии этого человека.');
        return;
      }

      const mappedPhotos = (data.photos ?? []).map(mapPhoto);
      setPersonPhotos(mappedPhotos);
      setPersonPhotosMessage(data.message ?? (mappedPhotos.length === 0 ? 'У этого человека пока нет фотографий.' : ''));
    } catch {
      setPersonPhotos([]);
      setPersonPhotosMessage('Не удалось связаться с API фотографий по человеку.');
    } finally {
      setPersonPhotosLoading(false);
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

      const data = await readJsonSafely<AuthResponse>(response);
      if (!response.ok) {
        setAuthMessage(data?.message ?? 'Не удалось выполнить авторизацию.');
        setAuthErrors(data?.fieldErrors ?? {});
        return;
      }

      setUser(data?.user ?? null);
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
    setUserMenuOpen(false);
    setPhotos([]);
    setPeople([]);
    setPeopleMessage('');
    setSelectedPersonId(null);
    setPersonPhotos([]);
    setPersonPhotosMessage('');
    setPersonRenameDraft('');
    setPhotoMenu(null);
  }

  function showToast(message: string) {
    setToastMessage(message);
    if (toastTimeoutRef.current !== null) {
      window.clearTimeout(toastTimeoutRef.current);
    }
    toastTimeoutRef.current = window.setTimeout(() => setToastMessage(''), 3200);
  }

  function openPhotoPicker() {
    fileInputRef.current?.click();
  }

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = '';

    if (files.length === 0) {
      return;
    }

    const invalidFile = files.find((file) => {
      const extension = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`;
      return !ALLOWED_UPLOAD_EXTENSIONS.includes(extension);
    });
    if (invalidFile) {
      showToast(`Файл ${invalidFile.name} не является поддерживаемой фотографией.`);
      return;
    }

    setUploadPending(true);
    showToast(`Загружаем ${files.length} фото...`);

    try {
      const formData = new FormData();
      files.forEach((file) => formData.append('files', file));

      const response = await fetch('/api/photos/upload', {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: formData,
      });

      const data = await readJsonSafely<PhotoUploadResponse>(response);
      if (!response.ok) {
        showToast(data?.message ?? 'Не удалось загрузить фотографии.');
        return;
      }

      await loadPhotos();
      await loadPeople();
      showToast(data?.message ?? `Загружено ${files.length} фото.`);
      setActiveTab('library');
    } catch {
      showToast('Ошибка загрузки фотографий. Проверьте соединение с сервером.');
    } finally {
      setUploadPending(false);
    }
  }

  async function handlePhotoDelete(photoId: number) {
    setPhotoMenu(null);

    try {
      const response = await fetch(`/api/photos/${photoId}/delete`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
        },
      });

      const data = await readJsonSafely<PhotoDeleteResponse>(response);
      if (!response.ok) {
        showToast(data?.message ?? 'Не удалось удалить фотографию.');
        return;
      }

      setPhotos((current) => current.filter((photo) => photo.id !== photoId));
      await loadPeople();
      showToast(data?.message ?? 'Фотография удалена.');
    } catch {
      showToast('Не удалось удалить фотографию. Проверьте соединение с сервером.');
    }
  }

  async function savePersonName() {
    if (selectedPersonId === null) {
      return;
    }

    setPersonRenamePending(true);
    try {
      const response = await fetch(`/api/people/${selectedPersonId}/rename`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ displayName: personRenameDraft.trim() }),
      });

      const data = await readJsonSafely<PersonRenameResponse>(response);
      if (!response.ok) {
        showToast(data?.message ?? 'Не удалось сохранить имя человека.');
        return;
      }

      const nextName = data?.person?.displayName ?? personRenameDraft.trim();
      setPeople((current) =>
        current.map((person) => (person.id === selectedPersonId ? { ...person, displayName: nextName } : person))
      );
      setPersonRenameDraft(nextName);
      showToast(nextName ? 'Имя человека сохранено.' : 'Имя очищено.');
    } catch {
      showToast('Не удалось сохранить имя человека. Проверьте соединение с сервером.');
    } finally {
      setPersonRenamePending(false);
    }
  }

  async function submitSemanticSearch() {
    const normalizedQuery = searchQuery.trim();
    if (!normalizedQuery) {
      setHasSearched(true);
      setSearchResults([]);
      setSearchMessage('Введите запрос, чтобы выполнить поиск по фотографии.');
      return;
    }

    setSearchPending(true);
    setHasSearched(true);
    setSearchMessage('');

    try {
      const response = await fetch('/api/photos/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ query: normalizedQuery }),
      });

      const data = await readJsonSafely<SearchResponse & { message?: string }>(response);
      if (!response.ok) {
        setSearchResults([]);
        setSearchMessage(data?.message ?? 'Не удалось выполнить поиск по фотографиям.');
        return;
      }

      const mappedResults = (data?.photos ?? []).map(mapSearchResult);
      setSearchResults(mappedResults);
      setSearchMessage(data?.message ?? (mappedResults.length === 0 ? 'Ничего не найдено.' : ''));
    } catch {
      setSearchResults([]);
      setSearchMessage('Ошибка связи с сервером поиска. Проверьте подключение и повторите запрос.');
    } finally {
      setSearchPending(false);
    }
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
            <span className="status-badge-label">{aiStatus.summary}</span>
            <strong>{aiStatus.details}</strong>
          </div>
          <div className="user-menu">
            <button
              className={`user-badge user-badge-button ${userMenuOpen ? 'active' : ''}`}
              type="button"
              aria-haspopup="menu"
              aria-expanded={userMenuOpen}
              onClick={() => setUserMenuOpen((current) => !current)}
            >
              <span className="user-badge-label">Пользователь</span>
              <strong>{user.username}</strong>
            </button>

            {userMenuOpen && (
              <button className="logout-dropdown-button" type="button" onClick={() => void handleLogout()}>
                Выйти из аккаунта
              </button>
            )}
          </div>
          <button className="glass-icon-button" aria-label="Открыть поиск" onClick={() => setActiveTab('search')}>
            <SearchIcon />
          </button>
          <button
            className="glass-icon-button primary"
            aria-label="Добавить фотографии"
            onClick={openPhotoPicker}
            disabled={uploadPending}
          >
            <PlusIcon />
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
        {activeTab === 'library' && (
          <LibraryView
            photos={photos}
            loading={photosLoading}
            onPhotoContextMenu={(photoId, event) => {
              event.preventDefault();
              setPhotoMenu({
                photoId,
                x: Math.min(event.clientX, window.innerWidth - 220),
                y: Math.min(event.clientY, window.innerHeight - 90),
              });
            }}
          />
        )}
        {activeTab === 'search' && (
          <SearchView
            aiStatus={aiStatus}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            pending={searchPending}
            results={searchResults}
            message={searchMessage}
            hasSearched={hasSearched}
            onSubmit={submitSemanticSearch}
          />
        )}
        {activeTab === 'people' && (
          <PeopleView
            aiStatus={aiStatus}
            people={people}
            loading={peopleLoading}
            message={peopleMessage}
            selectedPersonId={selectedPersonId}
            onSelectPerson={setSelectedPersonId}
            selectedPersonPhotos={personPhotos}
            selectedPersonPhotosLoading={personPhotosLoading}
            selectedPersonPhotosMessage={personPhotosMessage}
            personRenameDraft={personRenameDraft}
            personRenamePending={personRenamePending}
            onRenameDraftChange={setPersonRenameDraft}
            onRenameSave={savePersonName}
          />
        )}
      </main>

      {photoMenu && (
        <div ref={photoMenuRef} className="photo-context-menu" style={{ left: photoMenu.x, top: photoMenu.y }}>
          <button className="photo-context-delete" type="button" onClick={() => void handlePhotoDelete(photoMenu.photoId)}>
            Удалить фото
          </button>
        </div>
      )}

      {toastMessage && (
        <div className="upload-toast" role="status" aria-live="polite">
          {toastMessage}
        </div>
      )}

      <nav className="tabbar" aria-label="Primary">
        <div className={`tab-highlight ${activeTab}`} />
        {tabs.map((tab) => (
          <button key={tab.id} className={`tab-button ${activeTab === tab.id ? 'active' : ''}`} onClick={() => setActiveTab(tab.id)}>
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
            <button className={`auth-mode-button ${mode === 'register' ? 'active' : ''}`} onClick={() => onModeChange('register')}>
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

function LibraryView({
  photos,
  loading,
  onPhotoContextMenu,
}: {
  photos: PhotoItem[];
  loading: boolean;
  onPhotoContextMenu: (photoId: number, event: React.MouseEvent<HTMLElement>) => void;
}) {
  if (loading) {
    return (
      <section className="library-empty-state">
        <div className="library-empty-card">
          <h2>Загружаем медиатеку...</h2>
          <p>Список фотографий пользователя обновляется с сервера.</p>
        </div>
      </section>
    );
  }

  if (photos.length === 0) {
    return (
      <section className="library-empty-state">
        <div className="library-empty-card">
          <h2>Медиатека пока пуста</h2>
          <p>Нажмите на кнопку плюс справа сверху и загрузите первые фотографии в свою библиотеку.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="library-grid" aria-label="Photo library">
      {photos.map((photo) => (
        <article key={photo.id} className="photo-card" onContextMenu={(event) => onPhotoContextMenu(photo.id, event)}>
          <img src={photo.src} alt={photo.originalFilename} />
          <div className="photo-overlay" />
        </article>
      ))}
    </section>
  );
}

function SearchView({
  aiStatus,
  searchQuery,
  setSearchQuery,
  pending,
  results,
  message,
  hasSearched,
  onSubmit,
}: {
  aiStatus: AiStatusResponse;
  searchQuery: string;
  setSearchQuery: (value: string) => void;
  pending: boolean;
  results: SearchResultItem[];
  message: string;
  hasSearched: boolean;
  onSubmit: () => void;
}) {
  const isAiUnavailable = !aiStatus.enabled;
  const isSearchReady = aiStatus.enabled && aiStatus.state !== 'error' && aiStatus.state !== 'disabled';

  function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isSearchReady || pending) {
      return;
    }
    void onSubmit();
  }

  return (
    <section className="search-stage">
      <div className="search-intro">
        <h2>Поиск по фото</h2>
        <p>Опишите человека, объект, сцену или место на фотографии.</p>
      </div>

      <form className="search-composer" onSubmit={submitForm}>
        <div className="search-input-shell">
          <label className="sr-only-control" htmlFor="search-query">
            Поисковый запрос
          </label>
          <textarea
            id="search-query"
            className="search-textarea"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                if (!pending && isSearchReady) {
                  void onSubmit();
                }
              }
            }}
            placeholder="Например: девушка в очках рядом с машиной"
            rows={2}
          />

          <div className="search-toolbar">
            <div className="search-suggestions-inline">
              {['закат у моря', 'человек с собакой', 'ночной город'].map((item) => (
                <button key={item} type="button" className="glass-chip compact search-suggestion-chip" onClick={() => setSearchQuery(item)}>
                  {item}
                </button>
              ))}
            </div>

            <button type="submit" className="search-submit-button" aria-label="Запустить поиск" disabled={!isSearchReady || pending}>
              {pending ? 'Ищем...' : 'Найти'}
            </button>
          </div>
        </div>
      </form>

      {isAiUnavailable && (
        <div className="feature-status-card">
          <span className="feature-status-eyebrow">Поиск временно недоступен</span>
          <h3>AI-модуль отключён</h3>
          <p>Семантический поиск по фото недоступен, потому что AI-модуль сейчас не загружается.</p>
          <strong>{aiStatus.details}</strong>
        </div>
      )}

      {isSearchReady && (
        <section className="search-results-panel">
          {message && <div className="search-feedback-card">{message}</div>}

          {!hasSearched && !message && (
            <div className="search-feedback-card search-feedback-muted">
              Введите описание сцены и запустите поиск. Сервер вернёт top-10 самых близких фотографий из вашей медиатеки.
            </div>
          )}

          {hasSearched && !pending && results.length > 0 && (
            <div className="search-results-grid">
              {results.map((photo) => (
                <article key={photo.id} className="search-result-card">
                  <img src={photo.src} alt={photo.originalFilename} />
                  <div className="photo-overlay" />
                  <div className="search-result-meta">
                    <strong>{photo.originalFilename}</strong>
                    <span>Релевантность {photo.scorePercent.toFixed(1)}%</span>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      )}
    </section>
  );
}

function PeopleView({
  aiStatus,
  people,
  loading,
  message,
  selectedPersonId,
  onSelectPerson,
  selectedPersonPhotos,
  selectedPersonPhotosLoading,
  selectedPersonPhotosMessage,
  personRenameDraft,
  personRenamePending,
  onRenameDraftChange,
  onRenameSave,
}: {
  aiStatus: AiStatusResponse;
  people: PersonItem[];
  loading: boolean;
  message: string;
  selectedPersonId: number | null;
  onSelectPerson: (personId: number) => void;
  selectedPersonPhotos: PhotoItem[];
  selectedPersonPhotosLoading: boolean;
  selectedPersonPhotosMessage: string;
  personRenameDraft: string;
  personRenamePending: boolean;
  onRenameDraftChange: (value: string) => void;
  onRenameSave: () => void;
}) {
  const selectedPerson = people.find((person) => person.id === selectedPersonId) ?? null;
  const isAiUnavailable = !aiStatus.enabled;

  if (loading) {
    return (
      <section className="library-empty-state people-empty-state">
        <div className="library-empty-card">
          <h2>Ищем людей...</h2>
          <p>Собираем сгруппированные лица и фотографии из вашей медиатеки.</p>
        </div>
      </section>
    );
  }

  if (people.length === 0) {
    return (
      <section className="library-empty-state people-empty-state">
        <div className="library-empty-card feature-status-card">
          <span className="feature-status-eyebrow">Люди</span>
          <h2>{isAiUnavailable ? 'AI-модуль отключён' : 'Лица пока не найдены'}</h2>
          <p>
            {message ||
              (isAiUnavailable
                ? 'Группировка лиц недоступна, пока AI-модуль не активен в конфигурации проекта.'
                : 'Загрузите фотографии с крупными лицами или выполните переиндексацию людей для уже существующих фото.')}
          </p>
          <strong>{aiStatus.details}</strong>
        </div>
      </section>
    );
  }

  return (
    <section className="people-stage">
      {message && <div className="search-feedback-card">{message}</div>}

      <div className="people-layout">
        <section className="people-sidebar">
          <div className="people-grid" role="list" aria-label="Группы людей">
            {people.map((person) => {
              const title = person.displayName || person.fallbackName;
              return (
                <button
                  key={person.id}
                  type="button"
                  className={`person-tile ${selectedPersonId === person.id ? 'active' : ''}`}
                  onClick={() => onSelectPerson(person.id)}
                >
                  <div className="person-portrait-shell">
                    {person.previewUrl ? (
                      <img className="person-portrait" src={person.previewUrl} alt={title} />
                    ) : (
                      <div className="person-portrait person-portrait-placeholder">{title.slice(0, 1)}</div>
                    )}
                  </div>
                  <h3>{title}</h3>
                  <span className="person-count">
                    {person.photoCount} фото, {person.faceCount} лиц
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        <section className="people-detail-card">
          {selectedPerson && (
            <>
              <div className="people-detail-header">
                <div>
                  <span className="feature-status-eyebrow">Карточка человека</span>
                  <h2>{selectedPerson.displayName || selectedPerson.fallbackName}</h2>
                  <p>
                    Система объединила {selectedPerson.faceCount} найденных лиц в {selectedPerson.photoCount} фотографиях.
                  </p>
                </div>
                {selectedPerson.previewUrl ? (
                  <img className="people-detail-preview" src={selectedPerson.previewUrl} alt={selectedPerson.displayName || selectedPerson.fallbackName} />
                ) : (
                  <div className="people-detail-preview people-detail-preview-placeholder">
                    {(selectedPerson.displayName || selectedPerson.fallbackName).slice(0, 1)}
                  </div>
                )}
              </div>

              <form
                className="person-rename-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  void onRenameSave();
                }}
              >
                <label className="person-rename-field">
                  <span>Имя человека</span>
                  <input
                    value={personRenameDraft}
                    onChange={(event) => onRenameDraftChange(event.target.value)}
                    placeholder={selectedPerson.fallbackName}
                    maxLength={120}
                  />
                </label>
                <button className="auth-submit-button person-rename-submit" type="submit" disabled={personRenamePending}>
                  {personRenamePending ? 'Сохраняем...' : 'Сохранить имя'}
                </button>
              </form>

              {selectedPersonPhotosLoading && (
                <div className="search-feedback-card search-feedback-muted">Загружаем фотографии этого человека...</div>
              )}

              {!selectedPersonPhotosLoading && selectedPersonPhotosMessage && (
                <div className="search-feedback-card">{selectedPersonPhotosMessage}</div>
              )}

              {!selectedPersonPhotosLoading && selectedPersonPhotos.length > 0 && (
                <div className="people-photo-grid">
                  {selectedPersonPhotos.map((photo) => (
                    <article key={photo.id} className="people-photo-card">
                      <img src={photo.src} alt={photo.originalFilename} />
                      <div className="photo-overlay" />
                      <div className="search-result-meta">
                        <strong>{photo.originalFilename}</strong>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </>
          )}
        </section>
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

export default App;
