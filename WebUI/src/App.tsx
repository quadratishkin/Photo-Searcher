import { FormEvent, useEffect, useRef, useState } from 'react';

type TabId = 'library' | 'search' | 'people';
type AuthMode = 'login' | 'register';

type EntityPayload = {
  people: string[];
  objects: string[];
  scene: string[];
  actions: string[];
  attributes: string[];
  detectedObjectsEn: string[];
};

type PhotoItem = {
  id: number;
  src: string;
  originalFilename: string;
  processingStatus: string;
  fileExtension: string;
  fileSizeBytes: number;
  mimeType: string;
  hasEmbedding: boolean;
  embeddingDimension: number;
  embeddingModel: string;
  embeddingPretrainedTag: string;
  embeddingCreatedAt: string;
  captionModel: string;
  captionEn: string;
  captionRu: string;
  captionRuSynonyms: string[];
  searchTermsRu: string[];
  searchTermsEn: string[];
  searchSynonymsRu: string[];
  entityPayload: EntityPayload;
  captionCreatedAt: string;
  createdAt: string;
};

type SearchResultItem = PhotoItem & {
  score: number;
  scorePercent: number;
  entityScore: number;
  exactTermScore: number;
  synonymScore: number;
  groupCoverageScore: number;
  englishTermScore: number;
  embeddingScore: number;
  embeddingSimilarity: number;
  queryTermsRu: string[];
  querySynonymsRu: string[];
  matchedTermsRu: string[];
  matchedSynonymsRu: string[];
  matchedEntityGroups: Partial<Record<keyof Omit<EntityPayload, 'detectedObjectsEn'>, string[]>>;
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
  isStaff: boolean;
  isSuperuser: boolean;
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
  fileExtension: string;
  fileSizeBytes: number;
  mimeType: string;
  hasEmbedding: boolean;
  embeddingDimension: number;
  embeddingModel: string;
  embeddingPretrainedTag: string;
  embeddingCreatedAt: string;
  captionModel: string;
  captionEn: string;
  captionRu: string;
  captionRuSynonyms: string[];
  searchTermsRu: string[];
  searchTermsEn: string[];
  searchSynonymsRu: string[];
  entityPayload: Partial<EntityPayload>;
  captionCreatedAt: string;
  createdAt: string;
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

type PeopleMode = 'cards' | 'map';

type FaceMapFaceItem = {
  id: number;
  clusterId: string;
  personId: number | null;
  personLabel: string;
  previewUrl: string;
  photoId: number;
  photoUrl: string;
  photoFilename: string;
  bbox: number[];
  qualityScore: number;
  detectionScore: number;
  embeddingDimension: number;
  x: number;
  y: number;
};

type FaceClusterItem = {
  id: string;
  personId: number | null;
  label: string;
  faceCount: number;
  centroidX: number;
  centroidY: number;
};

type FaceMapResponse = {
  faces: FaceMapFaceItem[];
  clusters: FaceClusterItem[];
  clusterEps: number;
};

type FaceNeighborItem = {
  id: number;
  previewUrl: string;
  photoId: number;
  photoFilename: string;
  personId: number | null;
  personLabel: string;
  similarity: number;
  distance: number;
  sameCluster: boolean;
};

type FaceAnalysisResponse = {
  face: {
    id: number;
    previewUrl: string;
    photoId: number;
    photoUrl: string;
    photoFilename: string;
    personId: number | null;
    personLabel: string;
    bbox: number[];
    qualityScore: number;
    detectionScore: number;
    clusterFaceCount: number;
    centroidSimilarity: number;
  };
  neighbors: FaceNeighborItem[];
  clusterEps: number;
  message?: string;
};

const FACE_MAP_SCENE_SIZE = 1000;

type AiStatusResponse = {
  enabled: boolean;
  state: string;
  summary: string;
  details: string;
  reason: string;
};

type AdminSummary = {
  totalUsers: number;
  activeUsers: number;
  bannedUsers: number;
  staffUsers: number;
  totalPhotos: number;
  indexedPhotos: number;
  processingPhotos: number;
  failedPhotos: number;
  totalPeople: number;
  totalFaces: number;
};

type AdminHostInfo = {
  hostname: string;
  platform: string;
  python: string;
  timezone: string;
  serverTime: string;
};

type AdminModelCard = {
  title: string;
  value: string;
  details: string;
};

type AdminRuntime = {
  enabled: boolean;
  state: string;
  summary: string;
  details: string;
  reason: string;
  models: AdminModelCard[];
};

type AdminUserItem = {
  id: number;
  username: string;
  isActive: boolean;
  isStaff: boolean;
  isSuperuser: boolean;
  dateJoined: string;
  lastLogin: string;
  photoCount: number;
  personCount: number;
  faceCount: number;
};

type AdminOverviewResponse = {
  viewer: AuthUser;
  summary: AdminSummary;
  host: AdminHostInfo;
  runtime: AdminRuntime;
  users: AdminUserItem[];
};

type AdminUserAccessResponse = {
  message?: string;
  user?: {
    id: number;
    isActive: boolean;
  };
};

type SearchResponse = {
  query: string;
  normalizedRu: string;
  translatedQuery?: string;
  searchPromptEn?: string;
  queryTermsRu?: string[];
  querySynonymsRu?: string[];
  queryEntities?: Partial<EntityPayload>;
  queryAnalysisFallbackReason?: string;
  photos: Array<
    PhotoApiItem & {
      score: number;
      scorePercent: number;
      entityScore: number;
      exactTermScore: number;
      synonymScore: number;
      groupCoverageScore: number;
      englishTermScore: number;
      embeddingScore: number;
      embeddingSimilarity: number;
      queryTermsRu?: string[];
      querySynonymsRu?: string[];
      matchedTermsRu?: string[];
      matchedSynonymsRu?: string[];
      matchedEntityGroups?: Partial<Record<keyof Omit<EntityPayload, 'detectedObjectsEn'>, string[]>>;
    }
  >;
  topK: number;
  totalIndexedPhotos: number;
  skippedPhotos?: number;
  message?: string;
};

type SearchDebugInfo = {
  normalizedRu: string;
  translatedQuery: string;
  searchPromptEn: string;
  queryTermsRu: string[];
  querySynonymsRu: string[];
  queryEntities: EntityPayload;
  analysisFallbackReason: string;
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

function emptyEntityPayload(): EntityPayload {
  return {
    people: [],
    objects: [],
    scene: [],
    actions: [],
    attributes: [],
    detectedObjectsEn: [],
  };
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
  const [searchDebug, setSearchDebug] = useState<SearchDebugInfo | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [people, setPeople] = useState<PersonItem[]>([]);
  const [peopleLoading, setPeopleLoading] = useState(false);
  const [peopleMessage, setPeopleMessage] = useState('');
  const [peopleMode, setPeopleMode] = useState<PeopleMode>('cards');
  const [selectedPersonId, setSelectedPersonId] = useState<number | null>(null);
  const [personPhotos, setPersonPhotos] = useState<PhotoItem[]>([]);
  const [personPhotosLoading, setPersonPhotosLoading] = useState(false);
  const [personPhotosMessage, setPersonPhotosMessage] = useState('');
  const [personRenameDraft, setPersonRenameDraft] = useState('');
  const [personRenamePending, setPersonRenamePending] = useState(false);
  const [faceMapLoading, setFaceMapLoading] = useState(false);
  const [faceMapMessage, setFaceMapMessage] = useState('');
  const [faceMapData, setFaceMapData] = useState<FaceMapResponse>({ faces: [], clusters: [], clusterEps: 0 });
  const [selectedFaceId, setSelectedFaceId] = useState<number | null>(null);
  const [faceAnalysisLoading, setFaceAnalysisLoading] = useState(false);
  const [faceAnalysis, setFaceAnalysis] = useState<FaceAnalysisResponse | null>(null);
  const [uploadPending, setUploadPending] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [adminPanelOpen, setAdminPanelOpen] = useState(false);
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminMessage, setAdminMessage] = useState('');
  const [adminOverview, setAdminOverview] = useState<AdminOverviewResponse | null>(null);
  const [adminActionUserId, setAdminActionUserId] = useState<number | null>(null);
  const [photoMenu, setPhotoMenu] = useState<{ photoId: number; x: number; y: number } | null>(null);
  const [viewerPhoto, setViewerPhoto] = useState<PhotoItem | null>(null);
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
  const canAccessAdmin = Boolean(user?.isStaff || user?.isSuperuser);

  useEffect(() => {
    void loadCurrentUser();
    void loadAiStatus();
  }, []);

  useEffect(() => {
    if (!user) {
      setPhotos([]);
      setSearchResults([]);
      setSearchMessage('');
      setSearchDebug(null);
      setHasSearched(false);
      setPeople([]);
      setPeopleMessage('');
      setPeopleMode('cards');
      setSelectedPersonId(null);
      setPersonPhotos([]);
      setPersonPhotosMessage('');
      setPersonRenameDraft('');
      setFaceMapData({ faces: [], clusters: [], clusterEps: 0 });
      setFaceMapMessage('');
      setSelectedFaceId(null);
      setFaceAnalysis(null);
      setAdminPanelOpen(false);
      setAdminOverview(null);
      setAdminMessage('');
      setAdminActionUserId(null);
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
    if (!viewerPhoto) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setViewerPhoto(null);
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [viewerPhoto]);

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
    if (!adminPanelOpen) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setAdminPanelOpen(false);
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [adminPanelOpen]);

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

  useEffect(() => {
    if (!user || activeTab !== 'people' || peopleMode !== 'map' || faceMapLoading || faceMapData.faces.length > 0) {
      return;
    }

    void loadFaceMap();
  }, [activeTab, faceMapData.faces.length, faceMapLoading, peopleMode, user]);

  useEffect(() => {
    if (!user || selectedFaceId === null || activeTab !== 'people' || peopleMode !== 'map') {
      setFaceAnalysis(null);
      return;
    }

    void loadFaceAnalysis(selectedFaceId);
  }, [activeTab, peopleMode, selectedFaceId, user]);

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

  async function loadAdminOverview() {
    if (!canAccessAdmin) {
      return;
    }

    setAdminLoading(true);
    setAdminMessage('');
    try {
      const response = await fetch('/api/admin/overview');
      const data = await readJsonSafely<AdminOverviewResponse & { message?: string }>(response);
      if (!response.ok || !data) {
        setAdminOverview(null);
        setAdminMessage(data?.message ?? 'Не удалось загрузить данные админки.');
        return;
      }

      setAdminOverview(data);
    } catch {
      setAdminOverview(null);
      setAdminMessage('Не удалось связаться с административным API.');
    } finally {
      setAdminLoading(false);
    }
  }

  function mapPhoto(item: PhotoApiItem): PhotoItem {
    return {
      id: item.id,
      src: item.url,
      originalFilename: item.originalFilename,
      processingStatus: item.processingStatus,
      fileExtension: item.fileExtension,
      fileSizeBytes: item.fileSizeBytes,
      mimeType: item.mimeType,
      hasEmbedding: item.hasEmbedding,
      embeddingDimension: item.embeddingDimension,
      embeddingModel: item.embeddingModel,
      embeddingPretrainedTag: item.embeddingPretrainedTag,
      embeddingCreatedAt: item.embeddingCreatedAt,
      captionModel: item.captionModel,
      captionEn: item.captionEn,
      captionRu: item.captionRu,
      captionRuSynonyms: item.captionRuSynonyms ?? [],
      searchTermsRu: item.searchTermsRu ?? [],
      searchTermsEn: item.searchTermsEn ?? [],
      searchSynonymsRu: item.searchSynonymsRu ?? [],
      entityPayload: {
        ...emptyEntityPayload(),
        ...(item.entityPayload ?? {}),
      },
      captionCreatedAt: item.captionCreatedAt,
      createdAt: item.createdAt,
    };
  }

  function mapSearchResult(item: SearchResponse['photos'][number]): SearchResultItem {
    return {
      ...mapPhoto(item),
      score: item.score,
      scorePercent: item.scorePercent,
      entityScore: item.entityScore,
      exactTermScore: item.exactTermScore,
      synonymScore: item.synonymScore,
      groupCoverageScore: item.groupCoverageScore,
      englishTermScore: item.englishTermScore,
      embeddingScore: item.embeddingScore,
      embeddingSimilarity: item.embeddingSimilarity,
      queryTermsRu: item.queryTermsRu ?? [],
      querySynonymsRu: item.querySynonymsRu ?? [],
      matchedTermsRu: item.matchedTermsRu ?? [],
      matchedSynonymsRu: item.matchedSynonymsRu ?? [],
      matchedEntityGroups: item.matchedEntityGroups ?? {},
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

  async function loadFaceMap() {
    setFaceMapLoading(true);
    try {
      const response = await fetch('/api/people/face-map');
      const data = await readJsonSafely<FaceMapResponse & { message?: string }>(response);
      if (!response.ok || !data) {
        setFaceMapData({ faces: [], clusters: [], clusterEps: 0 });
        setFaceMapMessage(data?.message ?? 'Не удалось загрузить карту лиц.');
        setSelectedFaceId(null);
        return;
      }

      setFaceMapData({
        faces: data.faces ?? [],
        clusters: data.clusters ?? [],
        clusterEps: data.clusterEps ?? 0,
      });
      setFaceMapMessage((data.faces ?? []).length === 0 ? 'Пока нет готовых face embeddings для карты кластеров.' : '');
      setSelectedFaceId((current) => {
        if (current !== null && (data.faces ?? []).some((face) => face.id === current)) {
          return current;
        }
        return data.faces?.[0]?.id ?? null;
      });
    } catch {
      setFaceMapData({ faces: [], clusters: [], clusterEps: 0 });
      setFaceMapMessage('Не удалось связаться с API карты лиц.');
      setSelectedFaceId(null);
    } finally {
      setFaceMapLoading(false);
    }
  }

  async function loadFaceAnalysis(faceId: number) {
    setFaceAnalysisLoading(true);
    try {
      const response = await fetch(`/api/people/faces/${faceId}/analysis`);
      const data = await readJsonSafely<FaceAnalysisResponse>(response);
      if (!response.ok || !data) {
        setFaceAnalysis(null);
        return;
      }
      setFaceAnalysis(data);
    } catch {
      setFaceAnalysis(null);
    } finally {
      setFaceAnalysisLoading(false);
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
    setFaceMapData({ faces: [], clusters: [], clusterEps: 0 });
    setFaceMapMessage('');
    setSelectedFaceId(null);
    setFaceAnalysis(null);
    setSelectedPersonId(null);
    setPersonPhotos([]);
    setPersonPhotosMessage('');
    setPersonRenameDraft('');
    setPhotoMenu(null);
    setSearchDebug(null);
    setAdminPanelOpen(false);
    setAdminOverview(null);
    setAdminMessage('');
    setAdminActionUserId(null);
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
      await loadFaceMap();
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
      await loadFaceMap();
      showToast(data?.message ?? 'Фотография удалена.');
    } catch {
      showToast('Не удалось удалить фотографию. Проверьте соединение с сервером.');
    }
  }

  async function handleAdminUserAccess(targetUser: AdminUserItem) {
    setAdminActionUserId(targetUser.id);
    try {
      const response = await fetch(`/api/admin/users/${targetUser.id}/access`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ active: !targetUser.isActive }),
      });

      const data = await readJsonSafely<AdminUserAccessResponse>(response);
      if (!response.ok) {
        showToast(data?.message ?? 'Не удалось обновить статус пользователя.');
        return;
      }

      setAdminOverview((current) => {
        if (!current || !data?.user) {
          return current;
        }

        const users = current.users.map((userItem) =>
          userItem.id === data.user?.id ? { ...userItem, isActive: data.user.isActive } : userItem
        );
        const activeUsers = users.filter((userItem) => userItem.isActive).length;
        const bannedUsers = users.length - activeUsers;
        return {
          ...current,
          users,
          summary: {
            ...current.summary,
            activeUsers,
            bannedUsers,
          },
        };
      });

      showToast(data?.message ?? 'Статус пользователя обновлён.');
    } catch {
      showToast('Не удалось обновить статус пользователя. Проверьте соединение с сервером.');
    } finally {
      setAdminActionUserId(null);
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
      setSearchDebug(null);
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
        setSearchDebug(null);
        setSearchMessage(data?.message ?? 'Не удалось выполнить поиск по фотографиям.');
        return;
      }

      const mappedResults = (data?.photos ?? []).map(mapSearchResult);
      setSearchResults(mappedResults);
      setSearchDebug(
        data
          ? {
              normalizedRu: data.normalizedRu ?? normalizedQuery,
              translatedQuery: data.translatedQuery ?? '',
              searchPromptEn: data.searchPromptEn ?? '',
              queryTermsRu: data.queryTermsRu ?? [],
              querySynonymsRu: data.querySynonymsRu ?? [],
              queryEntities: {
                ...emptyEntityPayload(),
                ...(data.queryEntities ?? {}),
              },
              analysisFallbackReason: data.queryAnalysisFallbackReason ?? '',
            }
          : null
      );
      setSearchMessage(data?.message ?? (mappedResults.length === 0 ? 'Ничего не найдено.' : ''));
    } catch {
      setSearchResults([]);
      setSearchDebug(null);
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
          {canAccessAdmin && (
            <button
              className={`glass-icon-button admin-toggle-button ${adminPanelOpen ? 'active' : ''}`}
              aria-label="Открыть админку"
              onClick={() => {
                const nextOpen = !adminPanelOpen;
                setAdminPanelOpen(nextOpen);
                setUserMenuOpen(false);
                if (nextOpen) {
                  void loadAdminOverview();
                }
              }}
            >
              <AdminIcon />
            </button>
          )}
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
            onPhotoOpen={setViewerPhoto}
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
            debugInfo={searchDebug}
            message={searchMessage}
            hasSearched={hasSearched}
            onSubmit={submitSemanticSearch}
            onPhotoOpen={setViewerPhoto}
          />
        )}
        {activeTab === 'people' && (
          <PeopleView
            aiStatus={aiStatus}
            people={people}
            loading={peopleLoading}
            message={peopleMessage}
            mode={peopleMode}
            onModeChange={setPeopleMode}
            selectedPersonId={selectedPersonId}
            onSelectPerson={setSelectedPersonId}
            selectedPersonPhotos={personPhotos}
            selectedPersonPhotosLoading={personPhotosLoading}
            selectedPersonPhotosMessage={personPhotosMessage}
            personRenameDraft={personRenameDraft}
            personRenamePending={personRenamePending}
            onRenameDraftChange={setPersonRenameDraft}
            onRenameSave={savePersonName}
            onPhotoOpen={setViewerPhoto}
            faceMapData={faceMapData}
            faceMapLoading={faceMapLoading}
            faceMapMessage={faceMapMessage}
            selectedFaceId={selectedFaceId}
            onSelectFace={setSelectedFaceId}
            faceAnalysis={faceAnalysis}
            faceAnalysisLoading={faceAnalysisLoading}
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

      {viewerPhoto && <PhotoViewer photo={viewerPhoto} onClose={() => setViewerPhoto(null)} />}

      {canAccessAdmin && adminPanelOpen && (
        <AdminPanel
          overview={adminOverview}
          loading={adminLoading}
          message={adminMessage}
          pendingUserId={adminActionUserId}
          currentUserId={user.id}
          onClose={() => setAdminPanelOpen(false)}
          onRefresh={loadAdminOverview}
          onUserAccessToggle={handleAdminUserAccess}
        />
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

function AdminPanel({
  overview,
  loading,
  message,
  pendingUserId,
  currentUserId,
  onClose,
  onRefresh,
  onUserAccessToggle,
}: {
  overview: AdminOverviewResponse | null;
  loading: boolean;
  message: string;
  pendingUserId: number | null;
  currentUserId: number;
  onClose: () => void;
  onRefresh: () => Promise<void>;
  onUserAccessToggle: (user: AdminUserItem) => Promise<void>;
}) {
  const summaryCards = overview
    ? [
        { label: 'Пользователи', value: overview.summary.totalUsers, accent: 'blue' },
        { label: 'Активные', value: overview.summary.activeUsers, accent: 'mint' },
        { label: 'Заблокированные', value: overview.summary.bannedUsers, accent: 'red' },
        { label: 'Фотографии', value: overview.summary.totalPhotos, accent: 'amber' },
        { label: 'Проиндексировано', value: overview.summary.indexedPhotos, accent: 'blue' },
        { label: 'Лица', value: overview.summary.totalFaces, accent: 'mint' },
      ]
    : [];

  return (
    <div className="admin-overlay" role="presentation" onClick={onClose}>
      <section
        className="admin-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Административная панель"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="admin-drawer-header">
          <div>
            <span className="feature-status-eyebrow">Админка</span>
            <h2>Панель управления приложением</h2>
            <p>Быстрый обзор пользователей, состояния AI runtime и активности медиатеки.</p>
          </div>
          <div className="admin-drawer-actions">
            <button type="button" className="admin-ghost-button" onClick={() => void onRefresh()} disabled={loading}>
              Обновить
            </button>
            <button className="photo-viewer-close admin-close-button" type="button" aria-label="Закрыть админку" onClick={onClose}>
              ×
            </button>
          </div>
        </header>

        <div className="admin-drawer-scroll">
          {loading && <div className="search-feedback-card search-feedback-muted">Собираем статистику и состояние runtime...</div>}
          {!loading && message && <div className="search-feedback-card">{message}</div>}

          {!loading && overview && (
            <>
              <section className="admin-summary-grid">
                {summaryCards.map((card) => (
                  <article key={card.label} className={`admin-summary-card accent-${card.accent}`}>
                    <span>{card.label}</span>
                    <strong>{card.value}</strong>
                  </article>
                ))}
              </section>

              <section className="admin-info-grid">
                <article className="admin-info-card">
                  <div className="admin-section-heading">
                    <span className="feature-status-eyebrow">Хост</span>
                    <h3>Где сейчас запущено приложение</h3>
                  </div>
                  <dl className="admin-definition-list">
                    <div>
                      <dt>Компьютер</dt>
                      <dd>{overview.host.hostname}</dd>
                    </div>
                    <div>
                      <dt>Платформа</dt>
                      <dd>{overview.host.platform}</dd>
                    </div>
                    <div>
                      <dt>Python</dt>
                      <dd>{overview.host.python}</dd>
                    </div>
                    <div>
                      <dt>Часовой пояс</dt>
                      <dd>{overview.host.timezone}</dd>
                    </div>
                    <div>
                      <dt>Время сервера</dt>
                      <dd>{formatDate(overview.host.serverTime)}</dd>
                    </div>
                  </dl>
                </article>

                <article className="admin-info-card">
                  <div className="admin-section-heading">
                    <span className="feature-status-eyebrow">AI Runtime</span>
                    <h3>Статус и модели</h3>
                  </div>
                  <div className="admin-runtime-banner">
                    <strong>{overview.runtime.summary}</strong>
                    <span>{overview.runtime.details}</span>
                    {overview.runtime.reason && <p>{overview.runtime.reason}</p>}
                  </div>
                  <div className="admin-model-grid">
                    {overview.runtime.models.map((model) => (
                      <article key={`${model.title}-${model.value}`} className="admin-model-card">
                        <span>{model.title}</span>
                        <strong>{model.value}</strong>
                        <p>{model.details}</p>
                      </article>
                    ))}
                  </div>
                </article>
              </section>

              <section className="admin-users-section">
                <div className="admin-section-heading">
                  <span className="feature-status-eyebrow">Пользователи</span>
                  <h3>Кто есть в системе и сколько данных у каждого</h3>
                </div>
                <div className="admin-user-list">
                  {overview.users.map((account) => {
                    const isSelf = account.id === currentUserId;
                    return (
                      <article key={account.id} className={`admin-user-card ${account.isActive ? '' : 'is-blocked'}`}>
                        <div className="admin-user-main">
                          <div className="admin-user-title-row">
                            <div>
                              <h4>{account.username}</h4>
                              <p>
                                Добавлен {formatDate(account.dateJoined)}
                                {account.lastLogin ? ` • последний вход ${formatDate(account.lastLogin)}` : ' • ещё не входил'}
                              </p>
                            </div>
                            <div className="admin-user-badges">
                              <span className={`admin-role-badge ${account.isActive ? 'active' : 'blocked'}`}>
                                {account.isActive ? 'Активен' : 'Заблокирован'}
                              </span>
                              {account.isStaff && <span className="admin-role-badge">Staff</span>}
                              {account.isSuperuser && <span className="admin-role-badge">Superuser</span>}
                              {isSelf && <span className="admin-role-badge">Вы</span>}
                            </div>
                          </div>

                          <div className="admin-user-stats">
                            <div>
                              <span>Фотографии</span>
                              <strong>{account.photoCount}</strong>
                            </div>
                            <div>
                              <span>Люди</span>
                              <strong>{account.personCount}</strong>
                            </div>
                            <div>
                              <span>Лица</span>
                              <strong>{account.faceCount}</strong>
                            </div>
                          </div>
                        </div>

                        <button
                          type="button"
                          className={`admin-access-button ${account.isActive ? 'danger' : 'safe'}`}
                          disabled={pendingUserId === account.id || isSelf}
                          onClick={() => void onUserAccessToggle(account)}
                        >
                          {pendingUserId === account.id
                            ? 'Обновляем...'
                            : isSelf
                              ? 'Текущий аккаунт'
                              : account.isActive
                                ? 'Забанить'
                                : 'Разбанить'}
                        </button>
                      </article>
                    );
                  })}
                </div>
              </section>
            </>
          )}
        </div>
      </section>
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
  onPhotoOpen,
  onPhotoContextMenu,
}: {
  photos: PhotoItem[];
  loading: boolean;
  onPhotoOpen: (photo: PhotoItem) => void;
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
        <article
          key={photo.id}
          className="photo-card"
          onClick={() => onPhotoOpen(photo)}
          onContextMenu={(event) => onPhotoContextMenu(photo.id, event)}
        >
          <div className="photo-card-media">
            <img src={photo.src} alt={photo.originalFilename} />
            <div className="photo-overlay" />
            <div className={`photo-card-status status-${photo.processingStatus}`}>
              {getProcessingStatusLabel(photo.processingStatus)}
            </div>
          </div>

          <div className="photo-card-content">
            <strong className="photo-card-title" title={photo.originalFilename}>
              {photo.originalFilename}
            </strong>
            <p className="photo-card-caption">
              {photo.captionRu || photo.captionEn || 'Описание ещё не сгенерировано.'}
            </p>
            <EntityChipRow
              terms={photo.searchTermsRu}
              label="Теги"
              emptyLabel="Теги появятся после индексации"
              limit={4}
            />

            <dl className="photo-card-metadata">
              <div>
                <dt>Добавлено</dt>
                <dd>{formatDate(photo.createdAt)}</dd>
              </div>
              <div>
                <dt>Размер</dt>
                <dd>{formatFileSize(photo.fileSizeBytes)}</dd>
              </div>
              <div>
                <dt>Формат</dt>
                <dd>{photo.fileExtension || 'Не указан'}</dd>
              </div>
              <div>
                <dt>AI</dt>
                <dd>{photo.hasEmbedding || photo.captionRu || photo.captionEn ? 'Есть данные' : 'В обработке'}</dd>
              </div>
            </dl>
          </div>
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
  debugInfo,
  message,
  hasSearched,
  onSubmit,
  onPhotoOpen,
}: {
  aiStatus: AiStatusResponse;
  searchQuery: string;
  setSearchQuery: (value: string) => void;
  pending: boolean;
  results: SearchResultItem[];
  debugInfo: SearchDebugInfo | null;
  message: string;
  hasSearched: boolean;
  onSubmit: () => void;
  onPhotoOpen: (photo: SearchResultItem) => void;
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
        <p>Основной поиск теперь идёт по сущностям, тегам и нормализованным признакам, а embedding служит только дополнительным сигналом.</p>
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
                <article key={photo.id} className="search-result-card" onClick={() => onPhotoOpen(photo)}>
                  <img src={photo.src} alt={photo.originalFilename} />
                  <div className="photo-overlay" />
                  <div className="search-result-meta">
                    <strong>{photo.originalFilename}</strong>
                    <span>Релевантность {photo.scorePercent.toFixed(1)}%</span>
                    <span>Сущности {(photo.entityScore * 100).toFixed(1)}% • embedding {(photo.embeddingScore * 100).toFixed(1)}%</span>
                    {photo.matchedTermsRu.length > 0 && (
                      <EntityChipRow terms={photo.matchedTermsRu} label="Совпавшие термы" emptyLabel="" compact limit={4} />
                    )}
                    {photo.matchedSynonymsRu.length > 0 && (
                      <EntityChipRow terms={photo.matchedSynonymsRu} label="Совпавшие синонимы" emptyLabel="" compact limit={4} />
                    )}
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
  mode,
  onModeChange,
  selectedPersonId,
  onSelectPerson,
  selectedPersonPhotos,
  selectedPersonPhotosLoading,
  selectedPersonPhotosMessage,
  personRenameDraft,
  personRenamePending,
  onRenameDraftChange,
  onRenameSave,
  onPhotoOpen,
  faceMapData,
  faceMapLoading,
  faceMapMessage,
  selectedFaceId,
  onSelectFace,
  faceAnalysis,
  faceAnalysisLoading,
}: {
  aiStatus: AiStatusResponse;
  people: PersonItem[];
  loading: boolean;
  message: string;
  mode: PeopleMode;
  onModeChange: (mode: PeopleMode) => void;
  selectedPersonId: number | null;
  onSelectPerson: (personId: number) => void;
  selectedPersonPhotos: PhotoItem[];
  selectedPersonPhotosLoading: boolean;
  selectedPersonPhotosMessage: string;
  personRenameDraft: string;
  personRenamePending: boolean;
  onRenameDraftChange: (value: string) => void;
  onRenameSave: () => void;
  onPhotoOpen: (photo: PhotoItem) => void;
  faceMapData: FaceMapResponse;
  faceMapLoading: boolean;
  faceMapMessage: string;
  selectedFaceId: number | null;
  onSelectFace: (faceId: number) => void;
  faceAnalysis: FaceAnalysisResponse | null;
  faceAnalysisLoading: boolean;
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

      <div className="people-mode-switch" role="tablist" aria-label="Режим вкладки Люди">
        <button
          type="button"
          className={`people-mode-button ${mode === 'cards' ? 'active' : ''}`}
          aria-selected={mode === 'cards'}
          onClick={() => onModeChange('cards')}
        >
          Карточки людей
        </button>
        <button
          type="button"
          className={`people-mode-button ${mode === 'map' ? 'active' : ''}`}
          aria-selected={mode === 'map'}
          onClick={() => onModeChange('map')}
        >
          Карта кластеров
        </button>
      </div>

      {mode === 'cards' ? (
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
                    <span className="person-count">{person.photoCount} фото</span>
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
                      <article key={photo.id} className="people-photo-card" onClick={() => onPhotoOpen(photo)}>
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
      ) : (
        <PeopleClusterMapView
          data={faceMapData}
          loading={faceMapLoading}
          message={faceMapMessage}
          selectedFaceId={selectedFaceId}
          onSelectFace={onSelectFace}
          analysis={faceAnalysis}
          analysisLoading={faceAnalysisLoading}
        />
      )}
    </section>
  );
}

function PeopleClusterMapView({
  data,
  loading,
  message,
  selectedFaceId,
  onSelectFace,
  analysis,
  analysisLoading,
}: {
  data: FaceMapResponse;
  loading: boolean;
  message: string;
  selectedFaceId: number | null;
  onSelectFace: (faceId: number) => void;
  analysis: FaceAnalysisResponse | null;
  analysisLoading: boolean;
}) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const gestureBaseScaleRef = useRef(1);
  const interactionReleaseTimeoutRef = useRef<number | null>(null);
  const dragRef = useRef<{
    active: boolean;
    pointerId: number | null;
    startX: number;
    startY: number;
    originX: number;
    originY: number;
  }>({
    active: false,
    pointerId: null,
    startX: 0,
    startY: 0,
    originX: 0,
    originY: 0,
  });
  const [view, setView] = useState({ scale: 1, offsetX: 0, offsetY: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [isViewportActive, setIsViewportActive] = useState(false);

  function clampScale(value: number) {
    return Math.min(4, Math.max(0.65, value));
  }

  function buildCenteredView(scale: number) {
    const viewport = viewportRef.current;
    if (!viewport) {
      return { scale, offsetX: 0, offsetY: 0 };
    }

    const rect = viewport.getBoundingClientRect();
    return {
      scale,
      offsetX: (rect.width - FACE_MAP_SCENE_SIZE * scale) / 2,
      offsetY: (rect.height - FACE_MAP_SCENE_SIZE * scale) / 2,
    };
  }

  function zoomAt(clientX: number, clientY: number, nextScale: number) {
    const viewport = viewportRef.current;
    if (!viewport) {
      return;
    }

    const rect = viewport.getBoundingClientRect();
    setView((current) => {
      const clampedScale = clampScale(nextScale);
      const localX = clientX - rect.left;
      const localY = clientY - rect.top;
      const worldX = (localX - current.offsetX) / current.scale;
      const worldY = (localY - current.offsetY) / current.scale;
      return {
        scale: clampedScale,
        offsetX: localX - worldX * clampedScale,
        offsetY: localY - worldY * clampedScale,
      };
    });
  }

  function resetView() {
    setView(buildCenteredView(1));
  }

  function applyWheelInteraction(deltaX: number, deltaY: number, clientX: number, clientY: number, zoomIntent: boolean) {
    setIsViewportActive(true);
    if (interactionReleaseTimeoutRef.current !== null) {
      window.clearTimeout(interactionReleaseTimeoutRef.current);
    }
    interactionReleaseTimeoutRef.current = window.setTimeout(() => {
      if (!dragRef.current.active) {
        setIsViewportActive(false);
      }
    }, 220);

    if (zoomIntent) {
      const zoomFactor = Math.exp(-deltaY * 0.0025);
      zoomAt(clientX, clientY, view.scale * zoomFactor);
      return;
    }

    setView((current) => ({
      ...current,
      offsetX: current.offsetX - deltaX,
      offsetY: current.offsetY - deltaY,
    }));
  }

  function handleCanvasWheel(event: React.WheelEvent<HTMLDivElement>) {
    event.preventDefault();
    event.stopPropagation();

    applyWheelInteraction(event.deltaX, event.deltaY, event.clientX, event.clientY, event.ctrlKey || event.metaKey);
  }

  function handlePointerDown(event: React.PointerEvent<HTMLDivElement>) {
    if (event.pointerType === 'mouse' && event.button !== 0) {
      return;
    }
    if (event.target instanceof HTMLElement && event.target.closest('.people-cluster-node')) {
      return;
    }

    dragRef.current = {
      active: true,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: view.offsetX,
      originY: view.offsetY,
    };
    setIsPanning(true);
    setIsViewportActive(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: React.PointerEvent<HTMLDivElement>) {
    if (!dragRef.current.active || dragRef.current.pointerId !== event.pointerId) {
      return;
    }

    const deltaX = event.clientX - dragRef.current.startX;
    const deltaY = event.clientY - dragRef.current.startY;
    setView((current) => ({
      ...current,
      offsetX: dragRef.current.originX + deltaX,
      offsetY: dragRef.current.originY + deltaY,
    }));
  }

  function finishPointerInteraction(event: React.PointerEvent<HTMLDivElement>) {
    if (dragRef.current.pointerId === event.pointerId) {
      dragRef.current.active = false;
      dragRef.current.pointerId = null;
      setIsPanning(false);
      setIsViewportActive(false);
      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
    }
  }

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) {
      return;
    }

    const handleGestureStart = (event: Event) => {
      const gestureEvent = event as Event & { preventDefault: () => void };
      gestureEvent.preventDefault();
      event.stopPropagation();
      gestureBaseScaleRef.current = view.scale;
    };

    const handleGestureChange = (
      event: Event & { clientX?: number; clientY?: number; scale?: number; preventDefault: () => void }
    ) => {
      event.preventDefault();
      event.stopPropagation();
      const rect = viewport.getBoundingClientRect();
      const clientX = event.clientX ?? rect.left + rect.width / 2;
      const clientY = event.clientY ?? rect.top + rect.height / 2;
      const gestureScale = typeof event.scale === 'number' ? event.scale : 1;
      zoomAt(clientX, clientY, gestureBaseScaleRef.current * gestureScale);
    };

    const handleNativeWheel = (event: WheelEvent) => {
      event.preventDefault();
      event.stopPropagation();
      applyWheelInteraction(event.deltaX, event.deltaY, event.clientX, event.clientY, event.ctrlKey || event.metaKey);
    };

    viewport.addEventListener('wheel', handleNativeWheel, { passive: false });
    viewport.addEventListener('gesturestart', handleGestureStart as EventListener, { passive: false });
    viewport.addEventListener('gesturechange', handleGestureChange as EventListener, { passive: false });

    return () => {
      viewport.removeEventListener('wheel', handleNativeWheel);
      viewport.removeEventListener('gesturestart', handleGestureStart as EventListener);
      viewport.removeEventListener('gesturechange', handleGestureChange as EventListener);
    };
  }, [view.scale]);

  useEffect(() => {
    const root = document.documentElement;
    const body = document.body;
    const previousRootOverflow = root.style.overflow;
    const previousBodyOverflow = body.style.overflow;

    if (isViewportActive || isPanning) {
      root.style.overflow = 'hidden';
      body.style.overflow = 'hidden';
    }

    return () => {
      root.style.overflow = previousRootOverflow;
      body.style.overflow = previousBodyOverflow;
    };
  }, [isPanning, isViewportActive]);

  useEffect(() => {
    return () => {
      if (interactionReleaseTimeoutRef.current !== null) {
        window.clearTimeout(interactionReleaseTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (data.faces.length === 0) {
      return;
    }
    setView(buildCenteredView(1));
  }, [data.faces.length]);

  if (loading) {
    return (
      <section className="people-cluster-layout">
        <div className="people-cluster-canvas-shell search-feedback-card">Строим карту лиц и кластеров...</div>
        <aside className="people-cluster-detail-card search-feedback-card">Готовим explain-панель выбранного лица.</aside>
      </section>
    );
  }

  if (message) {
    return <div className="search-feedback-card">{message}</div>;
  }

  const clusterMembers = new Map<string, FaceMapFaceItem[]>();
  for (const face of data.faces) {
    const clusterFaceList = clusterMembers.get(face.clusterId) ?? [];
    clusterFaceList.push(face);
    clusterMembers.set(face.clusterId, clusterFaceList);
  }

  const clusterLayouts = data.clusters.map((cluster, index) => {
    const members = clusterMembers.get(cluster.id) ?? [];
    const centerX = cluster.centroidX * FACE_MAP_SCENE_SIZE * view.scale + view.offsetX;
    const centerY = cluster.centroidY * FACE_MAP_SCENE_SIZE * view.scale + view.offsetY;
    const radiusWorld = members.reduce((maxDistance, face) => {
      const dx = (face.x - cluster.centroidX) * FACE_MAP_SCENE_SIZE;
      const dy = (face.y - cluster.centroidY) * FACE_MAP_SCENE_SIZE;
      return Math.max(maxDistance, Math.hypot(dx, dy));
    }, 0);
    const radiusPx = Math.max(radiusWorld * view.scale + 44, 40);

    return {
      ...cluster,
      color: clusterColor(index),
      centerX,
      centerY,
      radiusPx,
    };
  });

  return (
    <section className="people-cluster-layout">
      <div className="people-cluster-canvas-shell">
        <div className="people-cluster-canvas-header">
          <div>
            <span className="feature-status-eyebrow">Карта лиц</span>
            <h2>Кластеры лиц</h2>
            <p>Здесь показано, как система сгруппировала найденные лица. Лица одного человека обычно находятся рядом и попадают в один кластер.</p>
          </div>
          <div className="people-cluster-stats people-cluster-stats-extended">
            <strong>{data.faces.length}</strong>
            <span>лиц</span>
            <strong>{data.clusters.length}</strong>
            <span>кластеров</span>
            <strong>{Math.round(view.scale * 100)}%</strong>
            <span>масштаб</span>
            <button type="button" className="people-cluster-reset" onClick={resetView}>
              Сбросить вид
            </button>
          </div>
        </div>

        <div
          ref={viewportRef}
          className={`people-cluster-canvas ${isPanning ? 'is-panning' : ''}`}
          tabIndex={0}
          onWheel={handleCanvasWheel}
          onFocus={() => setIsViewportActive(true)}
          onBlur={() => setIsViewportActive(false)}
          onPointerEnter={(event) => {
            event.currentTarget.focus({ preventScroll: true });
            setIsViewportActive(true);
          }}
          onPointerLeave={(event) => {
            finishPointerInteraction(event);
            setIsViewportActive(false);
          }}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={finishPointerInteraction}
          onPointerCancel={finishPointerInteraction}
        >
          <div className="people-cluster-scene">
            {clusterLayouts.map((cluster) => (
              <div
                key={cluster.id}
                className="people-cluster-ring"
                style={{
                  left: `${cluster.centerX}px`,
                  top: `${cluster.centerY}px`,
                  width: `${cluster.radiusPx * 2}px`,
                  height: `${cluster.radiusPx * 2}px`,
                  ['--cluster-color' as string]: cluster.color,
                }}
              >
                <span>{cluster.faceCount}</span>
              </div>
            ))}

            {data.faces.map((face) => {
              const cluster = clusterLayouts.find((item) => item.id === face.clusterId);
              return (
                <button
                  key={face.id}
                  type="button"
                  className={`people-cluster-node ${selectedFaceId === face.id ? 'active' : ''}`}
                  style={{
                    left: `${face.x * FACE_MAP_SCENE_SIZE * view.scale + view.offsetX}px`,
                    top: `${face.y * FACE_MAP_SCENE_SIZE * view.scale + view.offsetY}px`,
                    ['--cluster-color' as string]: cluster?.color ?? clusterColor(-1),
                  }}
                  onClick={(event) => {
                    event.stopPropagation();
                    onSelectFace(face.id);
                  }}
                  title={`${face.personLabel || 'Без имени'} • ${face.photoFilename}`}
                >
                  {face.previewUrl ? <img src={face.previewUrl} alt={face.photoFilename} /> : <span>{face.id}</span>}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <aside className="people-cluster-detail-card">
        {analysisLoading && <div className="search-feedback-card search-feedback-muted">Считаем соседей и похожесть выбранного лица...</div>}

        {!analysisLoading && !analysis && (
          <div className="search-feedback-card search-feedback-muted">
            Выберите лицо на карте, чтобы увидеть исходное фото, bbox, силу сходства с центром кластера и ближайших соседей.
          </div>
        )}

        {!analysisLoading && analysis && (
          <>
            <div className="people-cluster-selected">
              <div className="people-cluster-selected-preview">
                {analysis.face.previewUrl ? (
                  <img src={analysis.face.previewUrl} alt={analysis.face.photoFilename} />
                ) : (
                  <div className="people-cluster-selected-placeholder">Face</div>
                )}
              </div>
              <div>
                <span className="feature-status-eyebrow">Выбранное лицо</span>
                <h3>{analysis.face.personLabel || 'Без имени'}</h3>
                <p>{analysis.face.photoFilename}</p>
              </div>
            </div>

            <div className="people-cluster-analysis-grid">
              <div className="people-cluster-analysis-card">
                <span>Лиц в кластере</span>
                <strong>{analysis.face.clusterFaceCount}</strong>
              </div>
              <div className="people-cluster-analysis-card">
                <span>Похожесть к центру</span>
                <strong>{(analysis.face.centroidSimilarity * 100).toFixed(1)}%</strong>
              </div>
              <div className="people-cluster-analysis-card">
                <span>Quality score</span>
                <strong>{analysis.face.qualityScore.toFixed(3)}</strong>
              </div>
              <div className="people-cluster-analysis-card">
                <span>Detection score</span>
                <strong>{analysis.face.detectionScore.toFixed(3)}</strong>
              </div>
            </div>

            <div className="people-cluster-source-card">
              <h4>Исходное фото и bbox</h4>
              <img className="people-cluster-source-photo" src={analysis.face.photoUrl} alt={analysis.face.photoFilename} />
              <p>
                bbox: {analysis.face.bbox.map((value) => Math.round(value)).join(', ')}
              </p>
              <p>Порог кластеризации: {analysis.clusterEps.toFixed(2)}</p>
            </div>

            <div className="people-cluster-neighbors-card">
              <h4>Ближайшие лица</h4>
              <div className="people-cluster-neighbor-list">
                {analysis.neighbors.map((neighbor) => (
                  <button
                    key={neighbor.id}
                    type="button"
                    className={`people-cluster-neighbor ${neighbor.sameCluster ? 'same-cluster' : ''}`}
                    onClick={() => onSelectFace(neighbor.id)}
                  >
                    <div className="people-cluster-neighbor-preview">
                      {neighbor.previewUrl ? <img src={neighbor.previewUrl} alt={neighbor.photoFilename} /> : <span>{neighbor.id}</span>}
                    </div>
                    <div className="people-cluster-neighbor-copy">
                      <strong>{neighbor.personLabel || 'Без имени'}</strong>
                      <span>{neighbor.photoFilename}</span>
                      <span>
                        similarity {(neighbor.similarity * 100).toFixed(1)}% • distance {neighbor.distance.toFixed(3)}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </aside>
    </section>
  );
}

function EntityChipRow({
  terms,
  label,
  emptyLabel,
  compact = false,
  limit = 6,
}: {
  terms: string[];
  label: string;
  emptyLabel: string;
  compact?: boolean;
  limit?: number;
}) {
  const visibleTerms = terms.slice(0, limit);

  if (visibleTerms.length === 0) {
    return emptyLabel ? <div className="entity-chip-empty">{emptyLabel}</div> : null;
  }

  return (
    <div className="entity-chip-block">
      <span className="entity-chip-label">{label}</span>
      <div className={`entity-chip-row ${compact ? 'compact' : ''}`}>
        {visibleTerms.map((term) => (
          <span key={term} className={`entity-chip ${compact ? 'compact' : ''}`}>
            {term}
          </span>
        ))}
      </div>
    </div>
  );
}

function EntityGroupGrid({ entityPayload, title }: { entityPayload: EntityPayload; title: string }) {
  const groups: Array<{ key: keyof Omit<EntityPayload, 'detectedObjectsEn'>; label: string }> = [
    { key: 'people', label: 'Люди' },
    { key: 'objects', label: 'Объекты' },
    { key: 'scene', label: 'Сцена' },
    { key: 'actions', label: 'Действия' },
    { key: 'attributes', label: 'Признаки' },
  ];

  const hasAnyGroup = groups.some(({ key }) => entityPayload[key].length > 0);
  if (!hasAnyGroup) {
    return null;
  }

  return (
    <div className="entity-group-grid-shell">
      <h3>{title}</h3>
      <div className="entity-group-grid">
        {groups.map(({ key, label }) =>
          entityPayload[key].length > 0 ? (
            <div key={key} className="entity-group-card">
              <strong>{label}</strong>
              <div className="entity-chip-row compact">
                {entityPayload[key].map((term) => (
                  <span key={`${key}-${term}`} className="entity-chip compact">
                    {term}
                  </span>
                ))}
              </div>
            </div>
          ) : null
        )}
      </div>
    </div>
  );
}

function PhotoViewer({ photo, onClose }: { photo: PhotoItem; onClose: () => void }) {
  const displayCaption = photo.captionRu || photo.captionEn || 'Для этой фотографии caption пока не был сгенерирован.';
  const hasEnglishCaption = Boolean(photo.captionEn && photo.captionEn !== photo.captionRu);
  const metadataRows = [
    { label: 'Имя файла', value: photo.originalFilename },
    { label: 'Статус обработки', value: photo.processingStatus },
    { label: 'Дата добавления', value: formatDate(photo.createdAt) },
    { label: 'Размер файла', value: formatFileSize(photo.fileSizeBytes) },
    { label: 'MIME type', value: photo.mimeType || 'Не определён' },
    { label: 'Расширение', value: photo.fileExtension || 'Не указано' },
    { label: 'Embedding', value: photo.hasEmbedding ? 'Построен' : 'Нет' },
    { label: 'Размерность embedding', value: photo.embeddingDimension > 0 ? String(photo.embeddingDimension) : 'Нет данных' },
    { label: 'Embedding model', value: photo.embeddingModel || 'Не указана' },
    { label: 'Embedding tag', value: photo.embeddingPretrainedTag || 'Не указан' },
    { label: 'Embedding created', value: formatDate(photo.embeddingCreatedAt) },
    { label: 'Caption model', value: photo.captionModel || 'Не указана' },
    { label: 'Caption created', value: formatDate(photo.captionCreatedAt) },
  ];

  return (
    <div className="photo-viewer-backdrop" role="presentation" onClick={onClose}>
      <section
        className="photo-viewer-shell"
        role="dialog"
        aria-modal="true"
        aria-label={`Просмотр фото ${photo.originalFilename}`}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="photo-viewer-media-pane">
          <img className="photo-viewer-image" src={photo.src} alt={photo.originalFilename} />
        </div>

        <aside className="photo-viewer-meta-pane">
          <div className="photo-viewer-header">
            <div>
              <span className="feature-status-eyebrow">Расширенный просмотр</span>
              <h2>{photo.originalFilename}</h2>
            </div>
            <button className="photo-viewer-close" type="button" aria-label="Закрыть просмотр" onClick={onClose}>
              ×
            </button>
          </div>

          <div className="photo-viewer-meta-scroll">
            <div className="photo-viewer-section">
              <h3>Русский caption</h3>
              <p>{displayCaption}</p>
            </div>

            <div className="photo-viewer-section">
              <h3>Поисковый индекс</h3>
              <EntityChipRow terms={photo.searchTermsRu} label="Основные теги" emptyLabel="Теги ещё не сформированы" />
              {photo.searchSynonymsRu.length > 0 && (
                <EntityChipRow terms={photo.searchSynonymsRu} label="Синонимы" emptyLabel="" limit={10} />
              )}
            </div>

            <EntityGroupGrid entityPayload={photo.entityPayload} title="Сущности и признаки" />

            {hasEnglishCaption && (
              <div className="photo-viewer-section">
                <h3>English caption</h3>
                <p>{photo.captionEn}</p>
              </div>
            )}

            <div className="photo-viewer-section">
              <h3>Метаданные</h3>
              <dl className="photo-viewer-metadata-list">
                {metadataRows.map((item) => (
                  <div key={item.label} className="photo-viewer-metadata-row">
                    <dt>{item.label}</dt>
                    <dd>{item.value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </aside>
      </section>
    </div>
  );
}

function clusterColor(index: number): string {
  const palette = ['#88d2ff', '#ffbe78', '#8ea0ff', '#8be7c4', '#ff9a9a', '#f6e58d', '#d2a8ff', '#79e1ff'];
  return palette[((index % palette.length) + palette.length) % palette.length];
}

function formatFileSize(value: number): string {
  if (!Number.isFinite(value) || value <= 0) {
    return 'Неизвестно';
  }

  const units = ['B', 'KB', 'MB', 'GB'];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  return `${size.toFixed(size >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatDate(value: string): string {
  if (!value) {
    return 'Нет данных';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('ru-RU', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function getProcessingStatusLabel(status: string): string {
  switch (status) {
    case 'indexed':
      return 'Готово';
    case 'processing':
      return 'Обработка';
    case 'uploaded':
      return 'Загружено';
    case 'failed':
      return 'Ошибка';
    default:
      return status || 'Неизвестно';
  }
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

function AdminIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 3.5 5 6.35v4.12c0 4.08 2.45 7.82 6.23 9.5L12 20.5l.77-.53C16.55 18.29 19 14.55 19 10.47V6.35L12 3.5Zm0 1.62 5.5 2.23v3.12c0 3.43-2.03 6.59-5.16 8.06L12 18.76l-.34-.23C8.53 17.06 6.5 13.9 6.5 10.47V7.35L12 5.12Zm0 2.13a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5Zm-4 8.75c.54-1.71 2.12-2.75 4-2.75s3.46 1.04 4 2.75h-8Z"
        fill="currentColor"
      />
    </svg>
  );
}

export default App;
